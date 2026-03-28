/**
 * Supabase configuration.
 * Used when you add @supabase/supabase-js and need a client:
 *
 *   import { createClient } from '@supabase/supabase-js'
 *   import { supabaseUrl, supabaseAnonKey } from '../config/supabase'
 *   const supabase = createClient(supabaseUrl, supabaseAnonKey)
 */
export const supabaseUrl =
  import.meta.env.VITE_SUPABASE_URL ?? '';

export const supabaseAnonKey =
  import.meta.env.VITE_SUPABASE_ANON_KEY ?? '';
