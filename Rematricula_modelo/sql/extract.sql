-- SQL EXTRACT (placeholder)
-- Pega aquí la consulta final (sin credenciales).
-- El notebook original tenía una consulta larga con joins; por seguridad y porque estaba truncada, aquí va como plantilla.

SELECT TOP 100
    num_identificacion,
    COD_PERIODO,
    Periodo_Paga,
    ESTADOACTUAL,
    Programa,
    sede
    -- + todas las features numéricas/categóricas que uses
FROM CUN_REPOSITORIO.dbo.TU_TABLA_O_VISTA
WHERE COD_PERIODO IN ('2024A','2024B','2025B');  -- ajusta
