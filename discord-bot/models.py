"""
SQLAlchemy models for the Covenant Compliance Alert system.
Maps to tables created by 00002_obligaciones_discord.sql
"""

from datetime import datetime, date
from uuid import uuid4

from sqlalchemy import (
    Column, String, Text, Date, DateTime, Integer, ForeignKey,
    UniqueConstraint, Index, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Deuda(Base):
    """Existing deudas table — read-only from the bot's perspective."""
    __tablename__ = "deudas"

    id = Column(UUID(as_uuid=True), primary_key=True)
    nombre = Column(Text, nullable=False)
    acreedor = Column(Text, nullable=False)
    discord_canal_id = Column(Text)

    obligaciones = relationship("Obligacion", back_populates="deuda")


class Compromiso(Base):
    """Existing compromisos table — read-only reference."""
    __tablename__ = "compromisos"

    id = Column(UUID(as_uuid=True), primary_key=True)
    deuda_id = Column(UUID(as_uuid=True), ForeignKey("deudas.id"))
    clausula = Column(Text)
    descripcion = Column(Text, nullable=False)
    responsable = Column(Text)
    fecha_proxima = Column(Date)
    estado = Column(Text, nullable=False, default="pendiente")


class Obligacion(Base):
    """
    Obligaciones de cumplimiento con tracking de alertas Discord.
    Cada fila representa una obligación concreta con fecha de vencimiento
    que el bot debe monitorear.
    """
    __tablename__ = "obligaciones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    deuda_id = Column(UUID(as_uuid=True), ForeignKey("deudas.id"), nullable=False)
    compromiso_id = Column(UUID(as_uuid=True), ForeignKey("compromisos.id"), nullable=True)
    descripcion = Column(Text, nullable=False)
    area = Column(
        String,
        CheckConstraint(
            "area IN ('legal','tecnica','financiera','seguros',"
            "'ambiental','operaciones','compliance','gerencia')"
        ),
        nullable=False,
    )
    responsable_discord_id = Column(Text)  # Discord user or role ID
    fecha_vencimiento = Column(Date, nullable=False)
    estatus = Column(
        String,
        CheckConstraint(
            "estatus IN ('pendiente','en_progreso','completado','vencido','no_aplica')"
        ),
        nullable=False,
        default="pendiente",
    )
    notas = Column(Text)
    creado_en = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    actualizado_en = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    deuda = relationship("Deuda", back_populates="obligaciones")
    alertas = relationship("AlertaEnviada", back_populates="obligacion", cascade="all, delete-orphan")

    __table_args__ = (
        Index(
            "idx_obligaciones_vencimiento",
            fecha_vencimiento,
            postgresql_where=(estatus.in_(["pendiente", "en_progreso"])),
        ),
    )


class MapeoResponsable(Base):
    """
    Mapeo de áreas a IDs de Discord (usuario o rol).
    Permite que /asignar_responsable vincule un área a una mención.
    """
    __tablename__ = "mapeo_responsables"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    area = Column(
        String,
        CheckConstraint(
            "area IN ('legal','tecnica','financiera','seguros',"
            "'ambiental','operaciones','compliance','gerencia')"
        ),
        unique=True,
        nullable=False,
    )
    discord_id = Column(Text, nullable=False)
    tipo = Column(
        String,
        CheckConstraint("tipo IN ('user','role')"),
        nullable=False,
        default="role",
    )
    nombre = Column(Text)
    creado_en = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class AlertaEnviada(Base):
    """
    Registro de alertas ya enviadas — evita duplicados.
    La constraint UNIQUE(obligacion_id, dias_antes) impide enviar
    la misma alerta de 30 días dos veces para la misma obligación.
    """
    __tablename__ = "alertas_enviadas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    obligacion_id = Column(UUID(as_uuid=True), ForeignKey("obligaciones.id"), nullable=False)
    dias_antes = Column(Integer, nullable=False)  # 90, 30, 15, 3
    enviada_en = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    canal_discord_id = Column(Text)

    obligacion = relationship("Obligacion", back_populates="alertas")

    __table_args__ = (
        UniqueConstraint("obligacion_id", "dias_antes", name="uq_alerta_obligacion_dias"),
    )
