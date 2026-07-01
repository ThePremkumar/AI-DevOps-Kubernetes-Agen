'use client';

import React, { useState, useEffect } from 'react';
import { insforge } from '../services/insforge';
import { checkHealth, runInvestigation, getContexts, selectContext } from '../services/api';
import { useHealthQuery } from '../hooks/useInvestigation';

type StepName = 'Checking Pods' | 'Reading Logs' | 'Analyzing Events' | 'Inspecting Deployments' | 'Checking Networking' | 'AI Reasoning' | 'Root Cause Found';

interface ProgressStep {
  name: StepName;
  status: 'idle' | 'in-progress' | 'completed';
}

const INITIAL_STEPS: ProgressStep[] = [
  { name: 'Checking Pods', status: 'idle' },
  { name: 'Reading Logs', status: 'idle' },
  { name: 'Analyzing Events', status: 'idle' },
  { name: 'Inspecting Deployments', status: 'idle' },
  { name: 'Checking Networking', status: 'idle' },
  { name: 'AI Reasoning', status: 'idle' },
  { name: 'Root Cause Found', status: 'idle' }
];

export default function Home() {
  // Auth state
  const [user, setUser] = useState<any>(null);
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [isSignUp, setIsSignUp] = useState(false);
  const [authError, setAuthError] = useState('');
  const [isAuthLoading, setIsAuthLoading] = useState(true);

  // Cluster states
  const [contexts, setContexts] = useState<string[]>([]);
  const [activeContext, setActiveContext] = useState<string>('');
  const [isContextLoading, setIsContextLoading] = useState(false);

  // Investigation / Realtime states
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [steps, setSteps] = useState<ProgressStep[]>(INITIAL_STEPS);
  const [diagnosis, setDiagnosis] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState('');

  // History state
  const [history, setHistory] = useState<any[]>([]);

  // Health Query
  const { data: health, isLoading: isHealthLoading, error: healthError } = useHealthQuery();

  // Monitor Auth State
  useEffect(() => {
    const fetchSession = async () => {
      try {
        const { data, error } = await insforge.auth.getCurrentUser();
        if (data?.user) {
          setUser(data.user);
          fetchHistory(data.user.id);
          fetchClusters();
        }
      } catch (err) {
        console.error(err);
      } finally {
        setIsAuthLoading(false);
      }
    };
    fetchSession();
  }, []);

  // Fetch Clusters contexts
  const fetchClusters = async () => {
    try {
      const res = await getContexts();
      setContexts(res.contexts);
      if (res.current_context) {
        setActiveContext(res.current_context);
      }
    } catch (err) {
      console.error('Failed to load contexts', err);
    }
  };

  // Fetch History from InsForge DB
  const fetchHistory = async (userId: string) => {
    try {
      const { data, error } = await insforge.database
        .from('investigations')
        .select('*')
        .eq('user_id', userId)
        .order('created_at', { ascending: false })
        .limit(10);
      if (data) {
        setHistory(data);
      }
    } catch (err) {
      console.error('Failed to load history', err);
    }
  };

  // Handle Auth
  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');
    try {
      if (isSignUp) {
        const { data, error } = await insforge.auth.signUp({
          email: authEmail,
          password: authPassword,
        });
        if (error) throw error;
        if (data?.user) {
          setUser(data.user);
          fetchHistory(data.user.id);
          fetchClusters();
        }
      } else {
        const { data, error } = await insforge.auth.signInWithPassword({
          email: authEmail,
          password: authPassword,
        });
        if (error) throw error;
        if (data?.user) {
          setUser(data.user);
          fetchHistory(data.user.id);
          fetchClusters();
        }
      }
    } catch (err: any) {
      setAuthError(err.message || 'Authentication failed');
    }
  };

  // Handle Logout
  const handleLogout = async () => {
    await insforge.auth.signOut();
    setUser(null);
    setHistory([]);
    setContexts([]);
    setActiveContext('');
    setDiagnosis(null);
  };

  // Handle Context Switch
  const handleContextChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const ctx = e.target.value;
    setIsContextLoading(true);
    try {
      const res = await selectContext(ctx);
      if (res.success) {
        setActiveContext(ctx);
      } else {
        alert(`Failed to switch context: ${res.message}`);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsContextLoading(false);
    }
  };

  // Run SRE E2E Investigation with Realtime Status Updates
  const handleInvestigate = async () => {
    if (!user) return;
    setIsInvestigating(true);
    setDiagnosis(null);
    setErrorMsg('');
    setSteps(INITIAL_STEPS.map(s => ({ ...s, status: 'idle' })));

    try {
      // Connect and Subscribe to progress channel
      await insforge.realtime.connect();
      const subRes = await insforge.realtime.subscribe(`investigation:${user.id}`);
      
      // Listen for progress updates
      insforge.realtime.on('progress', (payload: any) => {
        const { step, status } = payload;
        setSteps(prev => prev.map(s => {
          if (s.name === step) {
            return { ...s, status };
          }
          return s;
        }));
      });

      // Call API
      const result = await runInvestigation(user.id);
      
      if (result.status === 'success') {
        setDiagnosis(result.diagnosis);
        fetchHistory(user.id);
      } else {
        setErrorMsg('Investigation returned an invalid status.');
      }
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.response?.data?.detail || 'Unable to connect to Kubernetes cluster. Please verify kubeconfig path and cluster access.');
    } finally {
      setIsInvestigating(false);
      // Clean up realtime subscription
      try {
        insforge.realtime.unsubscribe(`investigation:${user.id}`);
      } catch (e) {}
    }
  };

  // Handle history item selection to load previous diagnosis
  const handleSelectHistory = (item: any) => {
    setDiagnosis({
      root_cause: item.root_cause,
      explanation: item.explanation || 'No explanation recorded.',
      fix: item.fix || 'No suggested fix recorded.',
      kubectl_command: item.kubectl_command || '',
      confidence: item.confidence
    });
  };

  const getSystemStatusText = () => {
    if (isHealthLoading) return 'Checking orchestrator connectivity...';
    if (healthError || !health) return 'Agent Offline';
    return health.status === 'healthy' ? 'Cluster Orchestrator Online' : 'System Degraded';
  };

  // Calculate animated step progress height percentage
  const completedCount = steps.filter(s => s.status === 'completed').length;
  const progressPercent = (completedCount / steps.length) * 100;

  if (isAuthLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 text-slate-800">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs font-semibold text-slate-500 tracking-wider">Securing session...</span>
        </div>
      </main>
    );
  }

  // RENDER AUTHENTICATION GATING
  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center p-4 bg-slate-50 text-slate-900 font-sans">
        <div className="w-full max-w-md bg-white p-8 rounded-2xl border border-slate-200/80 shadow-xl space-y-6">
          <div className="text-center space-y-2">
            <h1 className="text-2xl font-black tracking-tight text-slate-900">
              KubeSRE Control
            </h1>
            <p className="text-slate-500 text-sm">
              Sign in to manage and diagnose cluster health
            </p>
          </div>

          <form onSubmit={handleAuth} className="space-y-4">
            {authError && (
              <div className="p-3 text-xs rounded-xl border border-red-200 bg-red-50 text-red-700 font-medium">
                {authError}
              </div>
            )}
            
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Email Address</label>
              <input
                type="email"
                required
                value={authEmail}
                onChange={e => setAuthEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full bg-white border border-slate-200 p-2.5 rounded-lg text-sm text-slate-800 focus:outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600 transition-all"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Password</label>
              <input
                type="password"
                required
                value={authPassword}
                onChange={e => setAuthPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-white border border-slate-200 p-2.5 rounded-lg text-sm text-slate-800 focus:outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600 transition-all"
              />
            </div>

            <button
              type="submit"
              className="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-bold transition-all shadow-md shadow-indigo-900/10 cursor-pointer text-sm"
            >
              {isSignUp ? 'Create Cloud Account' : 'Authenticate Console'}
            </button>
          </form>

          <div className="text-center pt-2">
            <button
              onClick={() => setIsSignUp(!isSignUp)}
              className="text-xs text-indigo-600 hover:text-indigo-700 font-semibold cursor-pointer"
            >
              {isSignUp ? 'Return to login' : 'Need console access? Register here'}
            </button>
          </div>
        </div>
      </main>
    );
  }

  // RENDER ENTERPRISE DASHBOARD
  return (
    <main className="flex min-h-screen flex-col items-center p-4 sm:p-12 bg-slate-50 text-slate-900 font-sans">
      <div className="w-full max-w-5xl flex flex-col gap-6">
        
        {/* Navigation / Header */}
        <header className="flex flex-col sm:flex-row gap-4 items-stretch sm:items-center justify-between border-b border-slate-200 pb-5">
          <div className="space-y-1">
            <h1 className="text-2xl font-black tracking-tight text-slate-900">
              KubeSRE Cloud Console
            </h1>
            <div className="flex items-center gap-2 text-xs text-slate-500 font-medium">
              <span className={`inline-block w-2.5 h-2.5 rounded-full ${
                isHealthLoading ? 'bg-slate-400 animate-pulse' : 
                healthError || !health ? 'bg-rose-500' : 'bg-emerald-500'
              }`} />
              <span>{getSystemStatusText()}</span>
            </div>
          </div>

          <div className="flex items-center justify-between sm:justify-end gap-4 bg-white p-2 border border-slate-200 rounded-xl shadow-sm">
            <span className="text-xs text-slate-600 font-semibold px-2">{user.email}</span>
            <button
              onClick={handleLogout}
              className="text-xs font-bold px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg cursor-pointer transition-colors border border-slate-200"
            >
              Disconnect
            </button>
          </div>
        </header>

        {/* Cluster Configuration / Main controls */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            
            {/* Control Panel */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-6">
              <div className="flex flex-col sm:flex-row items-stretch sm:items-end justify-between gap-4">
                
                {/* Cluster Select Context */}
                <div className="space-y-1.5 flex-1">
                  <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Kubernetes Active Cluster</label>
                  <select
                    value={activeContext}
                    onChange={handleContextChange}
                    disabled={isContextLoading || isInvestigating}
                    className="w-full bg-white border border-slate-200 p-2.5 rounded-lg text-sm text-slate-800 focus:outline-none focus:border-indigo-500 cursor-pointer shadow-sm"
                  >
                    {contexts.length === 0 ? (
                      <option>No Contexts Loaded</option>
                    ) : (
                      contexts.map(ctx => (
                        <option key={ctx} value={ctx}>{ctx}</option>
                      ))
                    )}
                  </select>
                </div>

                {/* Main Action Button */}
                <button
                  onClick={handleInvestigate}
                  disabled={isInvestigating || isContextLoading}
                  className="py-2.5 px-6 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-100 disabled:text-slate-400 text-white font-bold transition-all cursor-pointer text-sm shadow-sm"
                >
                  {isInvestigating ? 'Analyzing cluster logs...' : 'Investigate Cluster'}
                </button>
              </div>

              {/* Realtime progress tracker stepper with path visualizer */}
              {(isInvestigating || steps.some(s => s.status !== 'idle')) && (
                <div className="border border-slate-200 bg-slate-50 p-6 rounded-xl space-y-6 relative overflow-hidden">
                  <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block border-b border-slate-200 pb-2">
                    Orchestrated Diagnostic Stepper
                  </h4>
                  
                  {/* Vertical Progress Bar Connector */}
                  <div className="relative pl-6 space-y-6">
                    <div className="absolute left-[34px] top-3 bottom-3 w-1 bg-slate-200 rounded-full">
                      <div 
                        className="w-full bg-emerald-500 rounded-full transition-all duration-500" 
                        style={{ height: `${progressPercent}%` }}
                      />
                    </div>

                    {steps.map((step, idx) => {
                      const getSubtext = () => {
                        if (step.status !== 'in-progress') return '';
                        switch (step.name) {
                          case 'Checking Pods': return 'Scanning container status logs...';
                          case 'Reading Logs': return 'Retrieving stdout logs from problematic pods...';
                          case 'Analyzing Events': return 'Parsing cluster warnings and error codes...';
                          case 'Inspecting Deployments': return 'Verifying Deployment replicas and spec rules...';
                          case 'Checking Networking': return 'Testing Service selectors and endpoint matches...';
                          case 'AI Reasoning': return 'Evaluating findings with SRE reasoning model...';
                          default: return 'Wrapping up results...';
                        }
                      };

                      return (
                        <div key={idx} className="flex items-start gap-4 relative z-10">
                          {/* Circle Indicator */}
                          <div className={`w-6 h-6 rounded-full flex items-center justify-center border-2 transition-all duration-300 mt-0.5 ${
                            step.status === 'completed' 
                              ? 'bg-emerald-500 border-emerald-500 text-white' 
                              : step.status === 'in-progress'
                              ? 'bg-white border-indigo-650 shadow-[0_0_8px_rgba(79,70,229,0.3)] animate-pulse'
                              : 'bg-white border-slate-350'
                          }`}>
                            {step.status === 'completed' ? (
                              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                              </svg>
                            ) : (
                              <span className={`w-1.5 h-1.5 rounded-full ${step.status === 'in-progress' ? 'bg-indigo-600' : 'bg-slate-350'}`} />
                            )}
                          </div>

                          {/* Step Text details */}
                          <div className="flex flex-col text-left">
                            <span className={`text-xs font-mono font-bold transition-colors ${
                              step.status === 'completed' ? 'text-emerald-600 font-extrabold' :
                              step.status === 'in-progress' ? 'text-indigo-600 font-extrabold' : 'text-slate-400'
                            }`}>
                              {step.name}
                            </span>
                            {step.status === 'in-progress' && (
                              <span className="text-[10px] text-indigo-500 font-mono animate-pulse mt-0.5">
                                {getSubtext()}
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Error Message Box */}
            {errorMsg && (
              <div className="border border-rose-200 bg-rose-50 p-5 rounded-2xl text-sm text-rose-850 space-y-2">
                <span className="font-bold block text-base text-rose-800">⚠️ Investigation Connection Error</span>
                <p className="leading-relaxed text-xs font-mono">{errorMsg}</p>
                <div className="text-[10px] text-rose-700/80 pt-2 border-t border-rose-100 font-sans">
                  Ensure the target Kubernetes cluster is online and that local kubeconfig context is fully authorized.
                </div>
              </div>
            )}

            {/* SRE Diagnosis Output */}
            {diagnosis && (
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden text-left">
                {/* Header Banner */}
                <div className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
                  <div className="space-y-0.5">
                    <span className="text-[9px] font-bold tracking-widest text-slate-400 uppercase">SYSTEM DIAGNOSIS</span>
                    <h2 className="text-sm font-extrabold tracking-tight">AUTOMATED POST-MORTEM REPORT</h2>
                  </div>
                  <span className="text-xs font-mono bg-slate-800 border border-slate-700 px-2.5 py-1 rounded text-teal-400">
                    ID: {activeContext || 'unknown'}
                  </span>
                </div>

                {/* Metadata Row */}
                <div className="grid grid-cols-3 border-b border-slate-100 bg-slate-50/50 text-xs">
                  <div className="p-4 border-r border-slate-100">
                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Target Context</span>
                    <span className="font-mono text-slate-700 font-bold">{activeContext || 'default'}</span>
                  </div>
                  <div className="p-4 border-r border-slate-100">
                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Status</span>
                    <span className="inline-flex items-center gap-1.5 font-semibold text-slate-700">
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
                      <span>Anomalous</span>
                    </span>
                  </div>
                  <div className="p-4">
                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block mb-1">SRE Confidence</span>
                    <span className={`font-mono font-bold text-xs ${
                      diagnosis.confidence >= 80 ? 'text-emerald-600' : 'text-amber-600'
                    }`}>
                      {diagnosis.confidence}%
                    </span>
                  </div>
                </div>

                {/* Body Content */}
                <div className="p-6 space-y-6">
                  {/* Handle normal/healthy cluster state response */}
                  {diagnosis.root_cause === "No Critical Failures Found" ? (
                    <div className="text-center py-10 space-y-3">
                      <div className="inline-flex p-4 bg-emerald-50 border border-emerald-100 rounded-full text-emerald-600">
                        <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                        </svg>
                      </div>
                      <h3 className="text-sm font-bold text-slate-800">Cluster Status: Healthy</h3>
                      <p className="text-xs text-slate-500 max-w-sm mx-auto">
                        No critical warnings, CrashLoops, or image pulling problems found on the cluster.
                      </p>
                    </div>
                  ) : (
                    <>
                      {/* Root Cause Card */}
                      <div className="p-4 bg-rose-50/50 border border-rose-100 rounded-xl space-y-1">
                        <h3 className="text-[9px] font-bold text-rose-800 uppercase tracking-widest">DETECTED ROOT CAUSE</h3>
                        <p className="text-sm font-bold text-rose-950">
                          {diagnosis.root_cause}
                        </p>
                      </div>

                      {/* Diagnostic details table */}
                      <div className="border border-slate-150 rounded-xl overflow-hidden text-xs">
                        <div className="bg-slate-50/50 p-2.5 border-b border-slate-150 font-bold text-slate-600">Diagnostic Scope Metrics</div>
                        <div className="grid grid-cols-2 p-3 border-b border-slate-100">
                          <span className="text-slate-450 font-medium">Impact Severity</span>
                          <span className="text-rose-600 font-bold">CRITICAL</span>
                        </div>
                        <div className="grid grid-cols-2 p-3">
                          <span className="text-slate-450 font-medium">Resolution Priority</span>
                          <span className="text-indigo-650 font-bold">IMMEDIATE ACTION REQUIRED</span>
                        </div>
                      </div>

                      {/* Explanation */}
                      <div className="space-y-1.5">
                        <h3 className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">TECHNICAL INVESTIGATION</h3>
                        <p className="text-xs text-slate-600 leading-relaxed">
                          {diagnosis.explanation}
                        </p>
                      </div>

                      {/* Suggested Remediation Checklist */}
                      <div className="p-4 bg-indigo-50/30 border border-indigo-100 rounded-xl space-y-3">
                        <h3 className="text-[9px] font-bold text-indigo-800 uppercase tracking-widest">REMEDIATION ACTION CHECKLIST</h3>
                        <div className="space-y-2 text-xs text-slate-700">
                          <div className="flex items-start gap-2.5">
                            <span className="text-indigo-600 font-bold mt-0.5">1.</span>
                            <span className="leading-relaxed">{diagnosis.fix}</span>
                          </div>
                          <div className="flex items-start gap-2.5 border-t border-indigo-100/50 pt-2">
                            <span className="text-indigo-600 font-bold mt-0.5">2.</span>
                            <span className="leading-relaxed">Verify pod phase status using target descripter logs.</span>
                          </div>
                        </div>
                      </div>

                      {/* Kubectl Correction Command */}
                      {diagnosis.kubectl_command && (
                        <div className="space-y-2">
                          <h3 className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">RECOMMENDED COMMAND</h3>
                          <div className="relative group">
                            <pre className="bg-slate-950 p-4 rounded-xl font-mono text-[11px] text-zinc-300 overflow-x-auto whitespace-pre border border-slate-900">
                              {diagnosis.kubectl_command}
                            </pre>
                            <button
                              onClick={() => navigator.clipboard.writeText(diagnosis.kubectl_command)}
                              className="absolute top-2 right-2 text-[10px] bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-white px-2.5 py-1.5 rounded cursor-pointer transition-colors"
                            >
                              Copy
                            </button>
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            )}

          </div>

          {/* History Sidebar */}
          <div className="space-y-6">
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <h3 className="text-xs font-bold text-slate-500 tracking-wider uppercase border-b border-slate-100 pb-2">
                Investigation History
              </h3>
              {history.length === 0 ? (
                <div className="text-slate-400 text-xs text-center py-6 font-mono">No prior runs recorded.</div>
              ) : (
                <div className="space-y-2.5">
                  {history.map((h, i) => (
                    <button
                      key={i}
                      onClick={() => handleSelectHistory(h)}
                      className="w-full text-left border border-slate-150 p-3.5 rounded-xl bg-slate-50/50 hover:bg-slate-100/50 transition-all cursor-pointer hover:border-indigo-200 block group"
                    >
                      <div className="font-semibold text-slate-800 text-xs truncate group-hover:text-indigo-700 leading-tight">
                        {h.root_cause}
                      </div>
                      
                      <div className="mt-2.5 space-y-1">
                        <div className="flex justify-between text-[9px] text-slate-500 font-medium">
                          <span>Confidence</span>
                          <span>{h.confidence}%</span>
                        </div>
                        <div className="w-full bg-slate-200 h-1 rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full ${h.confidence >= 80 ? 'bg-indigo-600' : 'bg-amber-500'}`} 
                            style={{ width: `${h.confidence}%` }} 
                          />
                        </div>
                      </div>

                      <div className="flex justify-between text-[9px] text-slate-500 pt-2 mt-2 border-t border-slate-150/50 font-mono">
                        <span>ns: {h.namespace}</span>
                        <span>{new Date(h.created_at).toLocaleDateString()}</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

      </div>
    </main>
  );
}
