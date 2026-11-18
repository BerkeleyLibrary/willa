--
-- PostgreSQL database dump
--

SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET search_path TO public;


CREATE EXTENSION IF NOT EXISTS pgcrypto;
COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


DO $$ BEGIN
    IF to_regtype('"StepType"') IS NULL THEN
        CREATE TYPE "StepType" AS ENUM (
            'assistant_message',
            'embedding',
            'llm',
            'retrieval',
            'rerank',
            'run',
            'system_message',
            'tool',
            'undefined',
            'user_message'
        );
    END IF;
END $$;


SET default_tablespace = '';
SET default_table_access_method = heap;



CREATE TABLE IF NOT EXISTS "User" (
    id text DEFAULT gen_random_uuid() NOT NULL,
    "createdAt" timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "updatedAt" timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    metadata jsonb NOT NULL,
    identifier text NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (identifier)
);


CREATE TABLE IF NOT EXISTS "Thread" (
    id text DEFAULT gen_random_uuid() NOT NULL,
    "createdAt" timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "updatedAt" timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "deletedAt" timestamp(3) without time zone,
    name text,
    metadata jsonb NOT NULL,
    "userId" text,
    tags text[] DEFAULT ARRAY[]::text[],
    PRIMARY KEY (id),
    FOREIGN KEY ("userId") REFERENCES "User"(id) ON UPDATE CASCADE ON DELETE SET NULL
);


CREATE TABLE IF NOT EXISTS "Step" (
    id text DEFAULT gen_random_uuid() NOT NULL,
    "createdAt" timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "updatedAt" timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "parentId" text,
    "threadId" text,
    input text,
    metadata jsonb NOT NULL,
    name text,
    output text,
    type "StepType" NOT NULL,
    "showInput" text DEFAULT 'json'::text,
    "isError" boolean DEFAULT false,
    "startTime" timestamp(3) without time zone NOT NULL,
    "endTime" timestamp(3) without time zone NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY ("parentId") REFERENCES "Step"(id) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY ("threadId") REFERENCES "Thread"(id) ON UPDATE CASCADE ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS "Element" (
    id text DEFAULT gen_random_uuid() NOT NULL,
    "createdAt" timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "updatedAt" timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "threadId" text,
    "stepId" text NOT NULL,
    metadata jsonb NOT NULL,
    mime text,
    name text NOT NULL,
    "objectKey" text,
    url text,
    "chainlitKey" text,
    display text,
    size text,
    language text,
    page integer,
    props jsonb,
    PRIMARY KEY (id),
    FOREIGN KEY ("stepId") REFERENCES "Step"(id) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY ("threadId") REFERENCES "Thread"(id) ON UPDATE CASCADE ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS "Feedback" (
    id text DEFAULT gen_random_uuid() NOT NULL,
    "createdAt" timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "updatedAt" timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "stepId" text,
    name text NOT NULL,
    value double precision NOT NULL,
    comment text,
    PRIMARY KEY (id),
    FOREIGN KEY ("stepId") REFERENCES "Step"(id) ON UPDATE CASCADE ON DELETE SET NULL
);


CREATE TABLE IF NOT EXISTS _prisma_migrations (
    id character varying(36) NOT NULL,
    checksum character varying(64) NOT NULL,
    finished_at timestamp with time zone,
    migration_name character varying(255) NOT NULL,
    logs text,
    rolled_back_at timestamp with time zone,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    applied_steps_count integer DEFAULT 0 NOT NULL,
    PRIMARY KEY (id)
);


CREATE INDEX IF NOT EXISTS "Element_stepId_idx" ON "Element" USING btree ("stepId");

CREATE INDEX IF NOT EXISTS "Element_threadId_idx" ON "Element" USING btree ("threadId");

CREATE INDEX IF NOT EXISTS "Feedback_createdAt_idx" ON "Feedback" USING btree ("createdAt");

CREATE INDEX IF NOT EXISTS "Feedback_name_idx" ON "Feedback" USING btree (name);

CREATE INDEX IF NOT EXISTS "Feedback_name_value_idx" ON "Feedback" USING btree (name, value);

CREATE INDEX IF NOT EXISTS "Feedback_stepId_idx" ON "Feedback" USING btree ("stepId");

CREATE INDEX IF NOT EXISTS "Feedback_value_idx" ON "Feedback" USING btree (value);

CREATE INDEX IF NOT EXISTS "Step_createdAt_idx" ON "Step" USING btree ("createdAt");

CREATE INDEX IF NOT EXISTS "Step_endTime_idx" ON "Step" USING btree ("endTime");

CREATE INDEX IF NOT EXISTS "Step_name_idx" ON "Step" USING btree (name);

CREATE INDEX IF NOT EXISTS "Step_parentId_idx" ON "Step" USING btree ("parentId");

CREATE INDEX IF NOT EXISTS "Step_startTime_idx" ON "Step" USING btree ("startTime");

CREATE INDEX IF NOT EXISTS "Step_threadId_idx" ON "Step" USING btree ("threadId");

CREATE INDEX IF NOT EXISTS "Step_threadId_startTime_endTime_idx" ON "Step" USING btree ("threadId", "startTime", "endTime");

CREATE INDEX IF NOT EXISTS "Step_type_idx" ON "Step" USING btree (type);

CREATE INDEX IF NOT EXISTS "Thread_createdAt_idx" ON "Thread" USING btree ("createdAt");

CREATE INDEX IF NOT EXISTS "Thread_name_idx" ON "Thread" USING btree (name);

CREATE INDEX IF NOT EXISTS "User_identifier_idx" ON "User" USING btree (identifier);


--
-- PostgreSQL database dump complete
--
