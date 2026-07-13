with tab_excel:
        st.markdown("### 📚 Importar Biblioteca de Ejercicios (.xlsx / .csv)")
        archivo_subido = st.file_uploader("Arrastrá tu archivo excel o csv con los ejercicios:", type=["xlsx", "csv"])
        
        if archivo_subido is not None:
            try:
                df_ejercicios = pd.read_excel(archivo_subido) if archivo_subido.name.endswith('.xlsx') else pd.read_csv(archivo_subido)
                df_ejercicios.columns = df_ejercicios.columns.astype(str).str.strip()
                columnas_actuales = df_ejercicios.columns.tolist()
                
                # Mapeo corregido para detectar "grupo_muscular" con guion bajo
                col_nombre = next((c for c in columnas_actuales if c.lower() in ["nombre", "ejercicio", "name"]), None)
                col_grupo = next((c for c in columnas_actuales if c.lower() in ["grupo", "grupo muscular", "grupo_muscular", "musculo", "target", "patron"]), None)
                col_video = next((c for c in columnas_actuales if c.lower() in ["video", "link", "url", "link_video"]), None)
                
                if not col_nombre:
                    st.error("❌ El archivo debe tener al menos una columna llamada 'nombre' o 'ejercicio'.")
                else:
                    st.success(f"📋 Archivo detectado con éxito. Se encontraron {len(df_ejercicios)} filas.")
                    st.dataframe(df_ejercicios.head(10), use_container_width=True)
                    
                    if st.button("📥 CONFIRMAR E INYECTAR A LA BIBLIOTECA", use_container_width=True, type="primary"):
                        contador_insertados = 0
                        for _, fila in df_ejercicios.iterrows():
                            n_val = str(fila[col_nombre]).strip()
                            if n_val == "" or n_val.lower() == "nan": 
                                continue
                            # Asigna el patrón real del CSV, si no existe va a "General"
                            g_val = str(fila[col_grupo]).strip() if (col_grupo and str(fila[col_grupo]).strip().lower() != "nan") else "General"
                            v_val = str(fila[col_video]).strip() if (col_video and str(fila[col_video]).strip().lower() != "nan") else ""
                            
                            cursor.execute("""
                                INSERT OR IGNORE INTO biblioteca_ejercicios (nombre, grupo_muscular, link_video) 
                                VALUES (?, ?, ?)
                            """, (n_val, g_val, v_val))
                            contador_insertados += 1
                            
                        conn.commit()
                        st.success(f"🎉 ¡Biblioteca actualizada! Se procesaron {contador_insertados} ejercicios correctamente.")
                        st.rerun()
                        
            except Exception as e: 
                st.error(f"❌ Ocurrió un error al procesar el archivo: {e}")
