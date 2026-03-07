"use server";

import { createClient } from "@/lib/supabase/server";
import { revalidatePath } from "next/cache";

type Result = { success: true } | { success: false; error: string };

async function authCheck(): Promise<
  | { ok: true; supabase: ReturnType<typeof createClient> }
  | { ok: false; error: string }
> {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return { ok: false, error: "No autenticado" };

  const { data: usuario } = await supabase
    .from("usuarios")
    .select("rol")
    .eq("id", user.id)
    .single();
  if (!usuario || !["admin", "editor"].includes(usuario.rol)) {
    return { ok: false, error: "No autorizado" };
  }
  return { ok: true, supabase };
}

// --- DSCR ---

export async function addDscrPeriod(
  deudaId: string,
  data: {
    periodo: string;
    dscr_real: number | null;
    dscr_proyectado: number | null;
    cashflow: number | null;
    servicio_deuda: number | null;
    ingresos_operacionales: number | null;
    gastos_operativos: number | null;
    comision_fiduciaria: number | null;
    saldo_dsra: number | null;
  }
): Promise<Result> {
  const auth = await authCheck();
  if (!auth.ok) return { success: false, error: auth.error };

  const { error } = await auth.supabase
    .from("periodos_dscr")
    .insert({ deuda_id: deudaId, ...data });

  if (error) return { success: false, error: error.message };
  revalidatePath("/app/financiero");
  return { success: true };
}

export async function updateDscrPeriod(
  id: string,
  data: Record<string, unknown>
): Promise<Result> {
  const auth = await authCheck();
  if (!auth.ok) return { success: false, error: auth.error };

  const { error } = await auth.supabase
    .from("periodos_dscr")
    .update(data)
    .eq("id", id);

  if (error) return { success: false, error: error.message };
  revalidatePath("/app/financiero");
  return { success: true };
}

export async function deleteDscrPeriod(id: string): Promise<Result> {
  const auth = await authCheck();
  if (!auth.ok) return { success: false, error: auth.error };

  const { error } = await auth.supabase
    .from("periodos_dscr")
    .delete()
    .eq("id", id);

  if (error) return { success: false, error: error.message };
  revalidatePath("/app/financiero");
  return { success: true };
}

export async function importDscrFromCsv(
  deudaId: string,
  rows: {
    periodo: string;
    dscr_real: number | null;
    dscr_proyectado: number | null;
    cashflow: number | null;
    servicio_deuda: number | null;
    ingresos_operacionales: number | null;
    gastos_operativos: number | null;
    comision_fiduciaria: number | null;
    saldo_dsra: number | null;
  }[]
): Promise<Result> {
  const auth = await authCheck();
  if (!auth.ok) return { success: false, error: auth.error };

  const insertRows = rows.map((r) => ({ deuda_id: deudaId, ...r }));
  const { error } = await auth.supabase
    .from("periodos_dscr")
    .insert(insertRows);

  if (error) return { success: false, error: error.message };
  revalidatePath("/app/financiero");
  return { success: true };
}

// --- AMORTIZACION ---

export async function addAmortizacionRow(
  deudaId: string,
  data: { fecha_pago: string; capital: number; intereses: number }
): Promise<Result> {
  const auth = await authCheck();
  if (!auth.ok) return { success: false, error: auth.error };

  const { error } = await auth.supabase
    .from("amortizacion")
    .insert({ deuda_id: deudaId, ...data });

  if (error) return { success: false, error: error.message };
  revalidatePath("/app/financiero");
  return { success: true };
}

export async function deleteAmortizacionRow(id: string): Promise<Result> {
  const auth = await authCheck();
  if (!auth.ok) return { success: false, error: auth.error };

  const { error } = await auth.supabase
    .from("amortizacion")
    .delete()
    .eq("id", id);

  if (error) return { success: false, error: error.message };
  revalidatePath("/app/financiero");
  return { success: true };
}

export async function importAmortizacionFromCsv(
  deudaId: string,
  rows: { fecha_pago: string; capital: number; intereses: number }[]
): Promise<Result> {
  const auth = await authCheck();
  if (!auth.ok) return { success: false, error: auth.error };

  const insertRows = rows.map((r) => ({ deuda_id: deudaId, ...r }));
  const { error } = await auth.supabase
    .from("amortizacion")
    .insert(insertRows);

  if (error) return { success: false, error: error.message };
  revalidatePath("/app/financiero");
  return { success: true };
}
