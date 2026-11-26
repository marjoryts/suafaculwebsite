-- Telefone de contato do usuário (editável no perfil do app Mobile).
-- Opcional; o backend valida o formato (dígitos, espaço, +, -, parênteses).
ALTER TABLE public.usuarios ADD COLUMN IF NOT EXISTS telefone TEXT;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'usuarios_telefone_formato') THEN
        ALTER TABLE public.usuarios ADD CONSTRAINT usuarios_telefone_formato
            CHECK (telefone IS NULL OR telefone ~ '^[0-9 ()+-]{8,20}$');
    END IF;
END $$;

INSERT INTO public.suafacul_migracoes (versao) VALUES ('20261126000003') ON CONFLICT DO NOTHING;
