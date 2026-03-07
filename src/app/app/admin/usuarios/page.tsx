import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { UserTable } from "./user-table";

export default async function AdminUsuariosPage() {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data: usuarios } = await supabase
    .from("usuarios")
    .select("*")
    .order("creado_en", { ascending: true });

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-display text-2xl font-bold text-unergy-cream">
          Gestion de Usuarios
        </h1>
        <span className="text-sm text-gray-400">
          {usuarios?.length ?? 0} usuario(s) registrado(s)
        </span>
      </div>
      <div className="card-unergy overflow-x-auto">
        <UserTable usuarios={usuarios ?? []} currentUserId={user.id} />
      </div>
    </div>
  );
}
