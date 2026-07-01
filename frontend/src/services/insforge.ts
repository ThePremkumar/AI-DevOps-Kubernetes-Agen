import { createClient } from '@insforge/sdk';

const baseUrl = process.env.NEXT_PUBLIC_INSFORGE_URL || 'https://y8swi44k.us-east.insforge.app';
const anonKey = process.env.NEXT_PUBLIC_INSFORGE_ANON_KEY || 'ik_4327bb1f4e937e2b5d86e8a0e6a0e074';

export const insforge = createClient({
  baseUrl,
  anonKey,
});
export default insforge;
