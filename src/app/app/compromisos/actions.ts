"use server";

import { createClient } from "@/lib/supabase/server";
import { revalidatePath } from "next/cache";

const validEstados = ["pendiente", "en_progreso", "completado", "vencido"];

export async function updateCompromisoEstado(
  id: string,
  estado: string
): Promise<{ success: true } | { success: false; error: string }> {
  if (!validEstados.includes(estado)) {
    return { success: false, error: "Estado invalido" };
  }

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

  const { error } = await supabase
    .from("compromisos")
    .update({ estado })
    .eq("id", id);

  if (error) return { success: false, error: error.message };

  revalidatePath("/app/compromisos");
  return { success: true };
}
