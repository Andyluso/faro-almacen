-- ============================================================================
-- FARO: Configuración de Permisos y Storage en Supabase
-- Copia y pega esto en tu SQL Editor de Supabase y presiona "RUN"
-- ============================================================================

-- 1. Permitir lectura y escritura completa en las tablas de FARO
ALTER TABLE audits DISABLE ROW LEVEL SECURITY;
ALTER TABLE audit_items DISABLE ROW LEVEL SECURITY;
ALTER TABLE catalog_photos DISABLE ROW LEVEL SECURITY;

-- 2. Crear el bucket de fotos "garment-photos" automáticamente
INSERT INTO storage.buckets (id, name, public) 
VALUES ('garment-photos', 'garment-photos', true) 
ON CONFLICT (id) DO UPDATE SET public = true;

-- 3. Permitir subida y visualización de fotos públicas en garment-photos
DROP POLICY IF EXISTS "Public View Photos" ON storage.objects;
CREATE POLICY "Public View Photos" ON storage.objects 
FOR SELECT USING (bucket_id = 'garment-photos');

DROP POLICY IF EXISTS "Public Upload Photos" ON storage.objects;
CREATE POLICY "Public Upload Photos" ON storage.objects 
FOR INSERT WITH CHECK (bucket_id = 'garment-photos');

DROP POLICY IF EXISTS "Public Update Photos" ON storage.objects;
CREATE POLICY "Public Update Photos" ON storage.objects 
FOR UPDATE USING (bucket_id = 'garment-photos') WITH CHECK (bucket_id = 'garment-photos');

DROP POLICY IF EXISTS "Public Delete Photos" ON storage.objects;
CREATE POLICY "Public Delete Photos" ON storage.objects 
FOR DELETE USING (bucket_id = 'garment-photos');
