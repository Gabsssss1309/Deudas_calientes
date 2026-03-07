import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { FinancieroView } from "./financiero-view";
import { fetchSheetFinancieroData } from "@/lib/google-sheets";
import type { SheetFinancieroData } from "@/lib/google-sheets";

export default async function FinancieroPage() {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data: usuario } = await supabase
    .from("usuarios")
    .select("rol")
    .eq("id", user.id)
    .single();

  const canEdit =
    usuario?.rol === "admin" || usuario?.rol === "editor";

  // Fetch all deudas
  const { data: deudas } = await supabase
    .from("deudas")
    .select("*")
    .order("nombre");

  if (!deudas || deudas.length === 0) {
    return (
      <div>
        <h1 className="font-display text-2xl font-bold text-unergy-cream mb-6">
          Análisis Financiero
        </h1>
        <div className="card-unergy text-center py-12">
          <p className="text-gray-500">No hay deudas registradas.</p>
        </div>
      </div>
    );
  }

  // Fetch periodos_dscr and amortizacion for all deudas
  const deudaIds = deudas.map((d) => d.id);

  const [{ data: periodos }, { data: amortizacion }] = await Promise.all([
    supabase
      .from("periodos_dscr")
      .select("*")
      .in("deuda_id", deudaIds)
      .order("periodo"),
    supabase
      .from("amortizacion")
      .select("*")
      .in("deuda_id", deudaIds)
      .order("fecha_pago"),
  ]);

  // Fetch Google Sheet data for deudas that have a sheet_id configured
  const sheetDataMap: Record<string, SheetFinancieroData> = {};
  await Promise.all(
    deudas.map(async (deuda) => {
      const sheetId = (deuda.mapeo_cuentas as Record<string, string> | null)?.google_sheet_id;
      if (sheetId) {
        const data = await fetchSheetFinancieroData(sheetId);
        if (data) sheetDataMap[deuda.id] = data;
      }
    })
  );

  const deudasData = deudas.map((deuda) => ({
    deuda,
    periodos: (periodos ?? []).filter((p) => p.deuda_id === deuda.id),
    amortizacion: (amortizacion ?? []).filter((a) => a.deuda_id === deuda.id),
    sheetData: sheetDataMap[deuda.id] || null,
  }));

  return (
    <div>
      <h1 className="font-display text-2xl font-bold text-unergy-cream mb-2">
        Análisis Financiero
      </h1>
      <p className="text-sm text-gray-400 mb-6">
        Portafolio, rendimiento, covenants y condiciones de distribución por banco.
      </p>
      <FinancieroView deudasData={deudasData} canEdit={canEdit} />
    </div>
  );
}
