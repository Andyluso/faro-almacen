-- Ejecutar como administrador en el SQL Editor de TU proyecto Supabase.
-- Preparado para backend privado: requiere clave service_role o sb_secret_ SOLO en el servidor.
-- No borra datos. Revoca acceso directo de navegadores anónimos y usuarios no administradores.
BEGIN;
DO $$
DECLARE t text; p record;
BEGIN
  FOREACH t IN ARRAY ARRAY['audits','audit_items','catalog_photos'] LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('REVOKE ALL ON TABLE public.%I FROM anon, authenticated', t);
    EXECUTE format('GRANT ALL ON TABLE public.%I TO service_role', t);
    FOR p IN SELECT policyname FROM pg_policies WHERE schemaname='public' AND tablename=t LOOP
      EXECUTE format('DROP POLICY %I ON public.%I', p.policyname, t);
    END LOOP;
  END LOOP;
END $$;
DROP POLICY IF EXISTS "Public View Photos" ON storage.objects;
DROP POLICY IF EXISTS "Public Upload Photos" ON storage.objects;
DROP POLICY IF EXISTS "Public Update Photos" ON storage.objects;
DROP POLICY IF EXISTS "Public Delete Photos" ON storage.objects;
-- El bucket ya contenía Excels: hacerlo privado cierra sus enlaces públicos.
UPDATE storage.buckets SET public = false WHERE id = 'garment-photos';
INSERT INTO storage.buckets (id, name, public) VALUES ('faro-backups','faro-backups',false) ON CONFLICT (id) DO UPDATE SET public=false;
COMMIT;
