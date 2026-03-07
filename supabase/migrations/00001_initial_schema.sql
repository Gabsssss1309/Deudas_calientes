-- ============================================================
-- Debt Tracker — Initial Schema
-- All tables, RLS, triggers, seed data
-- ============================================================

-- 1. TABLES
-- ============================================================

create table public.usuarios (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null unique,
  nombre text,
  rol text not null default 'pendiente'
    check (rol in ('admin', 'editor', 'viewer', 'pendiente')),
  creado_en timestamptz not null default now()
);

create table public.deudas (
  id uuid primary key default gen_random_uuid(),
  nombre text not null,
  acreedor text not null,
  monto numeric not null,
  moneda text not null default 'USD',
  fecha_firma date,
  fecha_vencimiento date,
  discord_canal_id text,
  mapeo_cuentas jsonb,
  creado_en timestamptz not null default now()
);

create table public.compromisos (
  id uuid primary key default gen_random_uuid(),
  deuda_id uuid not null references public.deudas(id) on delete cascade,
  clausula text,
  descripcion text not null,
  tipo_trigger text check (tipo_trigger in ('periodico', 'evento', 'solicitud')),
  plazo_dias integer,
  frecuencia text,
  responsable text,
  fecha_proxima date,
  estado text not null default 'pendiente'
    check (estado in ('pendiente', 'en_progreso', 'completado', 'vencido')),
  notas text,
  creado_en timestamptz not null default now()
);

create table public.periodos_dscr (
  id uuid primary key default gen_random_uuid(),
  deuda_id uuid not null references public.deudas(id) on delete cascade,
  periodo text not null,
  dscr_real numeric,
  dscr_proyectado numeric,
  cashflow numeric,
  servicio_deuda numeric,
  ingresos_operacionales numeric,
  gastos_operativos numeric,
  comision_fiduciaria numeric,
  saldo_dsra numeric,
  fuente_archivo_url text,
  creado_en timestamptz not null default now()
);

create table public.amortizacion (
  id uuid primary key default gen_random_uuid(),
  deuda_id uuid not null references public.deudas(id) on delete cascade,
  fecha_pago date not null,
  capital numeric not null,
  intereses numeric not null,
  total numeric generated always as (capital + intereses) stored
);

create table public.archivos (
  id uuid primary key default gen_random_uuid(),
  deuda_id uuid not null references public.deudas(id) on delete cascade,
  tipo text check (tipo in ('contrato', 'fiducia', 'otro')),
  nombre_archivo text,
  url_supabase text not null,
  periodo text,
  creado_en timestamptz not null default now()
);

-- 2. HELPER FUNCTION: get current user's role
-- ============================================================

create or replace function public.user_role()
returns text
language sql
stable
security definer
as $$
  select rol from public.usuarios where id = auth.uid()
$$;

-- 3. ROW LEVEL SECURITY
-- ============================================================

-- usuarios
alter table public.usuarios enable row level security;

create policy "Users can read their own row"
  on public.usuarios for select
  using (id = auth.uid());

create policy "Admins can read all users"
  on public.usuarios for select
  using (public.user_role() = 'admin');

create policy "Admins can update all users"
  on public.usuarios for update
  using (public.user_role() = 'admin');

create policy "Users can insert their own row"
  on public.usuarios for insert
  with check (id = auth.uid());

-- deudas
alter table public.deudas enable row level security;

create policy "Active users can read deudas"
  on public.deudas for select
  using (public.user_role() in ('admin', 'editor', 'viewer'));

create policy "Admins can insert deudas"
  on public.deudas for insert
  with check (public.user_role() = 'admin');

create policy "Admins can update deudas"
  on public.deudas for update
  using (public.user_role() = 'admin');

-- compromisos
alter table public.compromisos enable row level security;

create policy "Active users can read compromisos"
  on public.compromisos for select
  using (public.user_role() in ('admin', 'editor', 'viewer'));

create policy "Editors and admins can insert compromisos"
  on public.compromisos for insert
  with check (public.user_role() in ('admin', 'editor'));

create policy "Editors and admins can update compromisos"
  on public.compromisos for update
  using (public.user_role() in ('admin', 'editor'));

-- periodos_dscr
alter table public.periodos_dscr enable row level security;

create policy "Active users can read periodos_dscr"
  on public.periodos_dscr for select
  using (public.user_role() in ('admin', 'editor', 'viewer'));

create policy "Editors and admins can insert periodos_dscr"
  on public.periodos_dscr for insert
  with check (public.user_role() in ('admin', 'editor'));

create policy "Editors and admins can update periodos_dscr"
  on public.periodos_dscr for update
  using (public.user_role() in ('admin', 'editor'));

-- amortizacion
alter table public.amortizacion enable row level security;

create policy "Active users can read amortizacion"
  on public.amortizacion for select
  using (public.user_role() in ('admin', 'editor', 'viewer'));

create policy "Admins can insert amortizacion"
  on public.amortizacion for insert
  with check (public.user_role() = 'admin');

create policy "Admins can update amortizacion"
  on public.amortizacion for update
  using (public.user_role() = 'admin');

-- archivos
alter table public.archivos enable row level security;

create policy "Active users can read archivos"
  on public.archivos for select
  using (public.user_role() in ('admin', 'editor', 'viewer'));

create policy "Editors and admins can insert archivos"
  on public.archivos for insert
  with check (public.user_role() in ('admin', 'editor'));

-- 4. TRIGGER: First user becomes admin, rest become pendiente
-- ============================================================

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  user_count int;
begin
  select count(*) into user_count from public.usuarios;

  insert into public.usuarios (id, email, nombre, rol)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data ->> 'full_name', new.raw_user_meta_data ->> 'name', ''),
    case when user_count = 0 then 'admin' else 'pendiente' end
  );

  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- 5. SEED: Initial FMO debt
-- ============================================================

insert into public.deudas (nombre, acreedor, monto, moneda, fecha_firma)
values (
  'FMO Sierra',
  'FMO (Nederlandse Financierings-Maatschappij voor Ontwikkelingslanden N.V.)',
  30000000,
  'USD',
  '2025-10-27'
);
