import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";

export default async function PendientePage() {
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

  if (usuario?.rol && usuario.rol !== "pendiente") {
    redirect("/app");
  }

  return (
    <div className="min-h-screen bg-unergy-deep-purple flex items-center justify-center">
      <div className="card-unergy max-w-lg w-full mx-4 text-center">
        <div className="text-5xl mb-4">&#9203;</div>
        <h1 className="font-display text-2xl font-bold text-unergy-deep-purple mb-3">
          Cuenta pendiente de aprobacion
        </h1>
        <p className="text-gray-600 mb-6">
          Tu cuenta ha sido registrada exitosamente. Un administrador debe
          aprobar tu acceso antes de que puedas usar la plataforma.
        </p>
        <p className="text-sm text-gray-400">
          Sesion iniciada como: {user.email}
        </p>
        <form action="/auth/signout" method="post" className="mt-6">
          <button
            type="submit"
            className="text-unergy-purple underline text-sm hover:opacity-80"
          >
            Cerrar sesion
          </button>
        </form>
      </div>
    </div>
  );
}
