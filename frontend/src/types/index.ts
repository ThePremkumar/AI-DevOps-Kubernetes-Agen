export interface HealthResponse {
  status: string;
  service: string;
}

export interface InvestigationResponse {
  status: string;
  investigation: {
    pods: {
      healthy: boolean;
      problematic_pods: Array<{
        name: string;
        namespace: string;
        status: string;
        phase: string;
      }>;
      total_pods_checked?: number;
      error?: string;
    };
    logs: Record<string, string>;
    events: Array<{
      namespace: string;
      object: string;
      reason: string;
      message: string;
      count: number;
      last_timestamp: string;
      error?: string;
    }> | Array<{error: string}>;
    deployments: Array<{
      name: string;
      namespace: string;
      desired_replicas: number;
      ready_replicas: number;
      available_replicas: number;
      conditions: Array<{
        type: string;
        status: string;
        message: string;
      }>;
      error?: string;
    }> | Array<{error: string}>;
    network: {
      network_issues: Array<{
        service_name: string;
        namespace: string;
        selector: Record<string, string>;
        issue: string;
      }>;
      services_count?: number;
      error?: string;
    };
  };
}
export interface DiagnosisResponse {
  status: string;
  diagnosis: {
    root_cause: string;
    explanation: string;
    fix: string;
    kubectl_command: string;
    confidence: number;
  };
}
