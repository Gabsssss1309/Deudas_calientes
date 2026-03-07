export type UserRole = "admin" | "editor" | "viewer" | "pendiente";

export interface Usuario {
  id: string;
  email: string;
  nombre: string | null;
  rol: UserRole;
  creado_en: string;
}

export interface Deuda {
  id: string;
  nombre: string;
  acreedor: string;
  monto: number;
  moneda: string;
  fecha_firma: string | null;
  fecha_vencimiento: string | null;
  discord_canal_id: string | null;
  mapeo_cuentas: Record<string, unknown> | null;
  creado_en: string;
}

export interface Compromiso {
  id: string;
  deuda_id: string;
  clausula: string | null;
  descripcion: string;
  tipo_trigger: "periodico" | "evento" | "solicitud" | null;
  plazo_dias: number | null;
  frecuencia: string | null;
  responsable: string | null;
  fecha_proxima: string | null;
  estado: "pendiente" | "en_progreso" | "completado" | "vencido";
  notas: string | null;
  creado_en: string;
}

export interface PeriodoDscr {
  id: string;
  deuda_id: string;
  periodo: string;
  dscr_real: number | null;
  dscr_proyectado: number | null;
  cashflow: number | null;
  servicio_deuda: number | null;
  ingresos_operacionales: number | null;
  gastos_operativos: number | null;
  comision_fiduciaria: number | null;
  saldo_dsra: number | null;
  fuente_archivo_url: string | null;
  creado_en: string;
}

export interface Amortizacion {
  id: string;
  deuda_id: string;
  fecha_pago: string;
  capital: number;
  intereses: number;
  total: number;
}

/** Shape returned by AI extraction — before DB insertion */
export interface ExtractedCompromiso {
  clausula: string;
  descripcion: string;
  tipo_trigger: string | null;
  plazo_dias: number | null;
  frecuencia: string | null;
  responsable_sugerido?: string;
  responsable?: string;
  notas: string | null;
  [key: string]: unknown; // allow extra fields from AI
}

export interface Archivo {
  id: string;
  deuda_id: string;
  tipo: "contrato" | "fiducia" | "otro" | null;
  nombre_archivo: string | null;
  url_supabase: string;
  periodo: string | null;
  creado_en: string;
}
