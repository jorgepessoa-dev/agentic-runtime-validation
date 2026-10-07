-- Disposable V1 database fixture only. Migrations reference these capability
-- roles in GRANT and policy declarations; a fresh initdb cluster has no roles.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='agentic_runtime_migration') THEN CREATE ROLE agentic_runtime_migration NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='agentic_runtime_runtime') THEN CREATE ROLE agentic_runtime_runtime NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='agentic_runtime_evaluator') THEN CREATE ROLE agentic_runtime_evaluator NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='agentic_runtime_verifier') THEN CREATE ROLE agentic_runtime_verifier NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='agentic_runtime_governance') THEN CREATE ROLE agentic_runtime_governance NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='agentic_promotion_executor') THEN CREATE ROLE agentic_promotion_executor NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='agentic_runtime_e1_promotion') THEN CREATE ROLE agentic_runtime_e1_promotion NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='agentic_runtime_e2_promotion') THEN CREATE ROLE agentic_runtime_e2_promotion NOLOGIN; END IF;
END $$;
