import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import Link from "next/link";
import { CompromisosTable } from "./compromisos-table";

export default async function CompromisosPage() {
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

  const { data: compromisos } = await supabase
    .from("compromisos")
    .select("*, deudas(nombre)")
    .order("creado_en", { ascending: false });

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-display text-2xl font-bold text-unergy-cream">
          Compromisos
        </h1>
        {canEdit && (
          <Link href="/app/compromisos/nuevo" className="btn-primary text-sm">
            + Nuevo desde PDF
          </Link>
        )}
      </div>

      <div className="card-unergy">
        <CompromisosTable
          compromisos={compromisos ?? []}
          canEdit={canEdit}
        />
      </div>
    </div>
  );
}
