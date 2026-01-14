def test_imports():
    from excel_to_sql.db.mssql import load_config_from_env, make_engine  # noqa: F401
    from excel_to_sql.convert import convert_dataframe_to_sql_schema  # noqa: F401
