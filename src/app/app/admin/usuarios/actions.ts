"use server";

import { createAdminClient } from "@/lib/supabase/admin";
import { createClient } from "@/lib/supabase/server";
import { revalidatePath } from "next/cache";

export async function updateUserRole(userId: string, newRole: string) {
  const validRoles = ["admin", "editor", "viewer", "pendiente"];
  if (!validRoles.includes(newRole)) {
    throw new Error("Rol invalido");
  }

  // Verify the caller is an admin
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) throw new Error("No autenticado");

  const { data: caller } = await supabase
    .from("usuarios")
    .select("rol")
    .eq("id", user.id)
    .single();

  if (caller?.rol !== "admin") throw new Error("No autorizado");

  // Prevent self-demotion
  if (userId === user.id && newRole !== "admin") {
    throw new Error("No puedes cambiar tu propio rol de admin");
  }

  // Use admin client to bypass RLS
  const adminClient = createAdminClient();
  const { error } = await adminClient
    .from("usuarios")
    .update({ rol: newRole })
    .eq("id", userId);

  if (error) throw new Error(error.message);

  revalidatePath("/app/admin/usuarios");
}
