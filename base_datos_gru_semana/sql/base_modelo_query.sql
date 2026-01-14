/*
Plantilla de extracción (ajusta según tu repositorio).
Debe retornar una tabla base con, al menos:

- Identificacion (ID estudiante)
- DescRF_Status (target)
- Variables base (DescRF_*, DescAM_*, etc.)

TIP: Puedes crear una vista o stored procedure y llamarla desde el script.
*/

SELECT TOP (1000)
    -- TODO: reemplaza por tus columnas reales
    Identificacion,
    DescRF_Status,
    DescRF_Modalidad,
    DescRF_ciclo,
    DescRF_SEMESTRE_MEN
FROM COE.TU_TABLA_O_VISTA;
