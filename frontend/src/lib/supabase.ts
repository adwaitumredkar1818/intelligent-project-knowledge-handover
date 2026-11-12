import { createClient } from "@supabase/supabase-js";

const supabaseUrl =
  process.env.NEXT_PUBLIC_SUPABASE_URL || "https://cenhylicwbbvspnwnapt.supabase.co";
const supabaseAnonKey =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  "sb_publishable_7mGVd48vRBXn-3CcwnkVFQ_sHUzEotH";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
