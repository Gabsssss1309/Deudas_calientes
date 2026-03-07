-- ============================================================
-- Debt Tracker — Discord Compliance Alerts
-- Tables: obligaciones, mapeo_responsables, alertas_enviadas
-- ============================================================

-- 1. OBLIGACIONES — Obligations with Discord alert tracking
-- ============================================================

create table public.obligaciones (
  id uuid primary key default gen_random_uuid(),
  deuda_id uuid not null references public.deudas(id) on delete cascade,
  compromiso_id uuid references public.compromisos(id) on delete set null,
  descripcion text not null,
  area text not null
    check (area in ('legal', 'tecnica', 'financiera', 'seguros', 'ambiental', 'operaciones', 'compliance', 'gerencia')),
  responsable_discord_id text, -- Discord user ID or role ID
  fecha_vencimiento date not null,
  estatus text not null default 'pendiente'
    check (estatus in ('pendiente', 'en_progreso', 'completado', 'vencido', 'no_aplica')),
  notas text,
  creado_en timestamptz not null default now(),
  actualizado_en timestamptz not null default now()
);

-- Index for the daily task runner query (filter by status + date range)
create index idx_obligaciones_vencimiento
  on public.obligaciones (fecha_vencimiento)
  where estatus in ('pendiente', 'en_progreso');

-- 2. MAPEO_RESPONSABLES — Map areas to Discord user/role IDs
-- ============================================================

create table public.mapeo_responsables (
  id uuid primary key default gen_random_uuid(),
  area text not null unique
    check (area in ('legal', 'tecnica', 'financiera', 'seguros', 'ambiental', 'operaciones', 'compliance', 'gerencia')),
  discord_id text not null,       -- Discord user or role ID
  tipo text not null default 'role'
    check (tipo in ('user', 'role')),
  nombre text,                    -- Friendly name (e.g., "Equipo Legal")
  creado_en timestamptz not null default now()
);

-- 3. ALERTAS_ENVIADAS — Track sent alerts (avoid duplicates)
-- ============================================================

create table public.alertas_enviadas (
  id uuid primary key default gen_random_uuid(),
  obligacion_id uuid not null references public.obligaciones(id) on delete cascade,
  dias_antes integer not null,    -- 90, 30, 15, or 3
  enviada_en timestamptz not null default now(),
  canal_discord_id text,
  unique (obligacion_id, dias_antes)
);

-- 4. RLS POLICIES
-- ============================================================

alter table public.obligaciones enable row level security;

create policy "Active users can read obligaciones"
  on public.obligaciones for select
  using (public.user_role() in ('admin', 'editor', 'viewer'));

create policy "Editors and admins can insert obligaciones"
  on public.obligaciones for insert
  with check (public.user_role() in ('admin', 'editor'));

create policy "Editors and admins can update obligaciones"
  on public.obligaciones for update
  using (public.user_role() in ('admin', 'editor'));

alter table public.mapeo_responsables enable row level security;

create policy "Active users can read mapeo_responsables"
  on public.mapeo_responsables for select
  using (public.user_role() in ('admin', 'editor', 'viewer'));

create policy "Admins can manage mapeo_responsables"
  on public.mapeo_responsables for all
  using (public.user_role() = 'admin');

alter table public.alertas_enviadas enable row level security;

create policy "Active users can read alertas_enviadas"
  on public.alertas_enviadas for select
  using (public.user_role() in ('admin', 'editor', 'viewer'));

create policy "Service can insert alertas_enviadas"
  on public.alertas_enviadas for insert
  with check (true);  -- Bot uses service role key

-- 5. UPDATED_AT TRIGGER
-- ============================================================

create or replace function public.update_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.actualizado_en = now();
  return new;
end;
$$;

create trigger obligaciones_updated_at
  before update on public.obligaciones
  for each row execute function public.update_updated_at();
