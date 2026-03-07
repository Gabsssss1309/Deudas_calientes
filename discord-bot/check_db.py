"""
Quick script to check if Discord bot tables exist and create them if needed.
Run once: python check_db.py
"""

import asyncio
from sqlalchemy import text
from db import engine


TABLES_SQL = """
CREATE TABLE IF NOT EXISTS public.obligaciones (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  deuda_id uuid NOT NULL REFERENCES public.deudas(id) ON DELETE CASCADE,
  compromiso_id uuid REFERENCES public.compromisos(id) ON DELETE SET NULL,
  descripcion text NOT NULL,
  area text NOT NULL
    CHECK (area IN ('legal', 'tecnica', 'financiera', 'seguros', 'ambiental', 'operaciones', 'compliance', 'gerencia')),
  responsable_discord_id text,
  fecha_vencimiento date NOT NULL,
  estatus text NOT NULL DEFAULT 'pendiente'
    CHECK (estatus IN ('pendiente', 'en_progreso', 'completado', 'vencido', 'no_aplica')),
  notas text,
  creado_en timestamptz NOT NULL DEFAULT now(),
  actualizado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.mapeo_responsables (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  area text NOT NULL UNIQUE
    CHECK (area IN ('legal', 'tecnica', 'financiera', 'seguros', 'ambiental', 'operaciones', 'compliance', 'gerencia')),
  discord_id text NOT NULL,
  tipo text NOT NULL DEFAULT 'role'
    CHECK (tipo IN ('user', 'role')),
  nombre text,
  creado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.alertas_enviadas (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  obligacion_id uuid NOT NULL REFERENCES public.obligaciones(id) ON DELETE CASCADE,
  dias_antes integer NOT NULL,
  enviada_en timestamptz NOT NULL DEFAULT now(),
  canal_discord_id text,
  UNIQUE (obligacion_id, dias_antes)
);
"""


async def check_and_create():
    async with engine.begin() as conn:
        # Check which tables exist
        result = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name IN "
            "('obligaciones', 'mapeo_responsables', 'alertas_enviadas')"
        ))
        existing = [row[0] for row in result.fetchall()]

        needed = {'obligaciones', 'mapeo_responsables', 'alertas_enviadas'}
        missing = needed - set(existing)

        if existing:
            print(f"[OK] Tables already exist: {', '.join(existing)}")

        if missing:
            print(f"[WARN] Missing tables: {', '.join(missing)}")
            print("Creating tables...")
            await conn.execute(text(TABLES_SQL))
            print("[OK] Tables created successfully!")
        else:
            print("[OK] All required tables exist. No action needed.")

        # Quick count check
        for table in sorted(needed):
            try:
                result = await conn.execute(text(f"SELECT count(*) FROM public.{table}"))
                count = result.scalar()
                print(f"   {table}: {count} rows")
            except Exception as e:
                print(f"   {table}: error reading - {e}")


if __name__ == "__main__":
    asyncio.run(check_and_create())
    print("\nDone! You can now start the bot with: python bot.py")
