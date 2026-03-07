"use server";

import { createClient } from "@/lib/supabase/server";
import { revalidatePath } from "next/cache";
import type { ExtractedCompromiso } from "@/types/database";

export async function saveCompromisos(
  deudaId: string,
  compromisos: ExtractedCompromiso[]
): Promise<{ success: true } | { success: false; error: string }> {
  try {
    // 1. Auth + role check
    const supabase = createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) return { success: false, error: "No autenticado" };

    const { data: usuario } = await supabase
      .from("usuarios")
      .select("rol")
      .eq("id", user.id)
      .single();
    if (!usuario || !["admin", "editor"].includes(usuario.rol)) {
      return { success: false, error: "No autorizado" };
    }

    // 2. Validate deuda exists
    const { data: deuda } = await supabase
      .from("deudas")
      .select("id")
      .eq("id", deudaId)
      .single();
    if (!deuda) return { success: false, error: "Deuda no encontrada" };

    // 3. Map extracted compromisos to DB rows (sanitize data from AI)
    const validTriggers = ["periodico", "evento", "solicitud"];
    const rows = compromisos.map((c) => {
      // Normalize tipo_trigger (remove accents, lowercase)
      const rawTrigger = (c.tipo_trigger || "")
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "");
      const tipo_trigger = validTriggers.includes(rawTrigger)
        ? rawTrigger
        : null;

      // Ensure plazo_dias is integer or null
      const plazo =
        c.plazo_dias != null ? parseInt(String(c.plazo_dias), 10) : null;

      return {
        deuda_id: deudaId,
        clausula: c.clausula || null,
        descripcion: c.descripcion || "Sin descripcion",
        tipo_trigger,
        plazo_dias: plazo != null && !isNaN(plazo) ? plazo : null,
        frecuencia: c.frecuencia || null,
        responsable: c.responsable_sugerido || c.responsable || null,
        fecha_proxima: null,
        estado: "pendiente" as const,
        notas: c.notas || null,
      };
    });

    // 4. Insert in batches to avoid payload limits
    const BATCH_SIZE = 50;
    for (let i = 0; i < rows.length; i += BATCH_SIZE) {
      const batch = rows.slice(i, i + BATCH_SIZE);
      const { error } = await supabase.from("compromisos").insert(batch);
      if (error) return { success: false, error: error.message };
    }

    revalidatePath("/app/compromisos");
    return { success: true };
  } catch (err) {
    console.error("saveCompromisos error:", err);
    return {
      success: false,
      error:
        err instanceof Error ? err.message : "Error inesperado al guardar",
    };
  }
}
