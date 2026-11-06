// Configurazione Supabase per Multe GAN.
// Copia questi due valori da Supabase: Project Settings > API (oppure "Connect" in alto).
// La chiave "anon" / "publishable" è pubblica per natura: i dati sono protetti dalle regole del database.
window.MULTE_GAN_CONFIG = {
  SUPABASE_URL: "https://xtrqqyrjjjmtwylxqndx.supabase.co",
  SUPABASE_ANON_KEY: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh0cnFxeXJqamptdHd5bHhxbmR4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTM5NjA0OTYsImV4cCI6MjEwOTUzNjQ5Nn0.PJpvtH5nishQfsP5PjubNRJc4rOUZNPccw6SO1WCQTQ",
  ADMIN_DOMAIN: "multegan.app",                   // il capitano entra con "capitano" = capitano@multegan.app
  // Link della colletta Satispay per pagare le multe (lascia "" per nascondere il pulsante)
  SATISPAY_URL: "https://web.satispay.com/download/qrcode/S6Y-SVN--E2FAA7F4-2A78-4FE2-B9E6-2CE3B0865B5A?locale=it"
};
