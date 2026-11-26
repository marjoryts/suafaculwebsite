-- ════════════════════════════════════════════════════════════════════════
-- SuaFacul — RLS e permissões
--
-- Modelo de acesso (ver docs/migracao-supabase.md):
--   * O ÚNICO cliente do banco é o backend Flask (site + API v1 do Mobile).
--     Ele conecta com o papel `suafacul_backend`: só DML nas tabelas do app,
--     sem DDL, sem TRUNCATE, sem acesso a auth/storage.
--   * A Data API do Supabase (PostgREST, chave anon/authenticated) fica
--     FECHADA: sem GRANT e com RLS ligado e nenhuma política para esses papéis.
--     Mesmo que alguém publique a chave anon, não há leitura nem escrita.
--   * As regras por usuário (cada um só vê os próprios favoritos/testes; só
--     admin gerencia conteúdo) são aplicadas no backend, que valida o token a
--     cada requisição e confere o papel no banco.
--
-- O papel é criado SEM login. Habilitar o login e definir a senha é um passo
-- manual (a senha não pode ficar no repositório):
--   ALTER ROLE suafacul_backend WITH LOGIN PASSWORD '<senha forte>';
-- ════════════════════════════════════════════════════════════════════════

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'suafacul_backend') THEN
        CREATE ROLE suafacul_backend NOLOGIN NOINHERIT;
    END IF;
END $$;

-- Projetos antigos deixam qualquer papel criar objetos em public.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO suafacul_backend;
-- Datas trocadas com a aplicação são texto em UTC: fixa o fuso da sessão.
ALTER ROLE suafacul_backend SET timezone TO 'UTC';
GRANT USAGE ON SCHEMA extensions TO suafacul_backend;
GRANT EXECUTE ON FUNCTION public.normalizar(TEXT), public.data_iso(TEXT) TO suafacul_backend;
-- Funções de extensão usadas por normalizar() e pelos índices trigram.
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA extensions TO suafacul_backend;

DO $$
DECLARE
    t TEXT;
    tabelas TEXT[] := ARRAY['usuarios', 'faculdades', 'cursos', 'vestibulares', 'favoritos',
                            'teste_vocacional_resultados', 'automacao_logs', 'refresh_tokens',
                            'cursos_catalogo', 'suafacul_migracoes'];
    papel TEXT;
BEGIN
    FOREACH t IN ARRAY tabelas LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);

        -- Fecha a Data API: nenhum privilégio para os papéis do PostgREST.
        EXECUTE format('REVOKE ALL ON public.%I FROM PUBLIC', t);
        FOREACH papel IN ARRAY ARRAY['anon', 'authenticated'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = papel) THEN
                EXECUTE format('REVOKE ALL ON public.%I FROM %I', t, papel);
            END IF;
        END LOOP;

        -- Backend: DML (o controle de migrations é somente leitura).
        IF t = 'suafacul_migracoes' THEN
            EXECUTE format('GRANT SELECT ON public.%I TO suafacul_backend', t);
            EXECUTE format('DROP POLICY IF EXISTS backend_leitura ON public.%I', t);
            EXECUTE format('CREATE POLICY backend_leitura ON public.%I FOR SELECT TO suafacul_backend USING (true)', t);
        ELSE
            EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON public.%I TO suafacul_backend', t);
            EXECUTE format('DROP POLICY IF EXISTS backend_acesso ON public.%I', t);
            EXECUTE format('CREATE POLICY backend_acesso ON public.%I FOR ALL TO suafacul_backend '
                           'USING (true) WITH CHECK (true)', t);
        END IF;
    END LOOP;
END $$;

-- Sequências das colunas IDENTITY (INSERT precisa de USAGE).
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO suafacul_backend;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        EXECUTE 'REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon';
        EXECUTE 'REVOKE EXECUTE ON FUNCTION public.normalizar(TEXT), public.data_iso(TEXT), public.definir_updated_at() FROM anon';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        EXECUTE 'REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM authenticated';
        EXECUTE 'REVOKE EXECUTE ON FUNCTION public.normalizar(TEXT), public.data_iso(TEXT), public.definir_updated_at() FROM authenticated';
    END IF;
END $$;
REVOKE EXECUTE ON FUNCTION public.normalizar(TEXT), public.data_iso(TEXT), public.definir_updated_at() FROM PUBLIC;

INSERT INTO public.suafacul_migracoes (versao) VALUES ('20261126000002') ON CONFLICT DO NOTHING;
