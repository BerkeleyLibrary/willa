--
-- PostgreSQL database dump
--

SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET search_path TO public;


CREATE EXTENSION IF NOT EXISTS pgcrypto;
COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


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


SET default_tablespace = '';
SET default_table_access_method = heap;


CREATE TABLE "Element" (
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
    props jsonb
);


CREATE TABLE "Feedback" (
    id text DEFAULT gen_random_uuid() NOT NULL,
    "createdAt" timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "updatedAt" timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "stepId" text,
    name text NOT NULL,
    value double precision NOT NULL,
    comment text
);


CREATE TABLE "Step" (
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
    "endTime" timestamp(3) without time zone NOT NULL
);


CREATE TABLE "Thread" (
    id text DEFAULT gen_random_uuid() NOT NULL,
    "createdAt" timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "updatedAt" timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "deletedAt" timestamp(3) without time zone,
    name text,
    metadata jsonb NOT NULL,
    "userId" text,
    tags text[] DEFAULT ARRAY[]::text[]
);


CREATE TABLE "User" (
    id text DEFAULT gen_random_uuid() NOT NULL,
    "createdAt" timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "updatedAt" timestamp(3) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    metadata jsonb NOT NULL,
    identifier text NOT NULL
);


CREATE TABLE _prisma_migrations (
    id character varying(36) NOT NULL,
    checksum character varying(64) NOT NULL,
    finished_at timestamp with time zone,
    migration_name character varying(255) NOT NULL,
    logs text,
    rolled_back_at timestamp with time zone,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    applied_steps_count integer DEFAULT 0 NOT NULL
);


ALTER TABLE ONLY "Element"
    ADD CONSTRAINT "Element_pkey" PRIMARY KEY (id);

ALTER TABLE ONLY "Feedback"
    ADD CONSTRAINT "Feedback_pkey" PRIMARY KEY (id);

ALTER TABLE ONLY "Step"
    ADD CONSTRAINT "Step_pkey" PRIMARY KEY (id);

ALTER TABLE ONLY "Thread"
    ADD CONSTRAINT "Thread_pkey" PRIMARY KEY (id);

ALTER TABLE ONLY "User"
    ADD CONSTRAINT "User_pkey" PRIMARY KEY (id);

ALTER TABLE ONLY _prisma_migrations
    ADD CONSTRAINT _prisma_migrations_pkey PRIMARY KEY (id);


CREATE INDEX "Element_stepId_idx" ON "Element" USING btree ("stepId");

CREATE INDEX "Element_threadId_idx" ON "Element" USING btree ("threadId");

CREATE INDEX "Feedback_createdAt_idx" ON "Feedback" USING btree ("createdAt");

CREATE INDEX "Feedback_name_idx" ON "Feedback" USING btree (name);

CREATE INDEX "Feedback_name_value_idx" ON "Feedback" USING btree (name, value);

CREATE INDEX "Feedback_stepId_idx" ON "Feedback" USING btree ("stepId");

CREATE INDEX "Feedback_value_idx" ON "Feedback" USING btree (value);

CREATE INDEX "Step_createdAt_idx" ON "Step" USING btree ("createdAt");

CREATE INDEX "Step_endTime_idx" ON "Step" USING btree ("endTime");

CREATE INDEX "Step_name_idx" ON "Step" USING btree (name);

CREATE INDEX "Step_parentId_idx" ON "Step" USING btree ("parentId");

CREATE INDEX "Step_startTime_idx" ON "Step" USING btree ("startTime");

CREATE INDEX "Step_threadId_idx" ON "Step" USING btree ("threadId");

CREATE INDEX "Step_threadId_startTime_endTime_idx" ON "Step" USING btree ("threadId", "startTime", "endTime");

CREATE INDEX "Step_type_idx" ON "Step" USING btree (type);

CREATE INDEX "Thread_createdAt_idx" ON "Thread" USING btree ("createdAt");

CREATE INDEX "Thread_name_idx" ON "Thread" USING btree (name);

CREATE INDEX "User_identifier_idx" ON "User" USING btree (identifier);


CREATE UNIQUE INDEX "User_identifier_key" ON "User" USING btree (identifier);


ALTER TABLE ONLY "Element"
    ADD CONSTRAINT "Element_stepId_fkey" FOREIGN KEY ("stepId") REFERENCES "Step"(id) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY "Element"
    ADD CONSTRAINT "Element_threadId_fkey" FOREIGN KEY ("threadId") REFERENCES "Thread"(id) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY "Feedback"
    ADD CONSTRAINT "Feedback_stepId_fkey" FOREIGN KEY ("stepId") REFERENCES "Step"(id) ON UPDATE CASCADE ON DELETE SET NULL;

ALTER TABLE ONLY "Step"
    ADD CONSTRAINT "Step_parentId_fkey" FOREIGN KEY ("parentId") REFERENCES "Step"(id) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY "Step"
    ADD CONSTRAINT "Step_threadId_fkey" FOREIGN KEY ("threadId") REFERENCES "Thread"(id) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY "Thread"
    ADD CONSTRAINT "Thread_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"(id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--
