# --- 3. TAG MANAGER (Database Sync Fix) ---
    with t3:
        st.subheader("🏷️ Tag Control Center")
        
        # New Tag Input (Auto-Capitalize)
        new_tag_input = st.text_input("Add New Tag").strip().upper() 
        
        if st.button("➕ Save Tag"):
            if new_tag_input:
                # Upsert taaki duplicate na bane
                supabase.table("custom_tags").upsert({"tag_name": new_tag_input}).execute()
                st.success(f"Tag '{new_tag_input}' Saved Successfully!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.warning("Pehle kuch likho bhai!")
        
        st.divider()
        st.markdown("#### 📋 Full Database Tag Inventory")
        
        # Fresh fetch from DB
        all_db_tags = get_tags()
        
        if all_db_tags:
            # Colorful Grid Style
            cols = st.columns(4)
            for i, tag in enumerate(all_db_tags):
                with cols[i % 4]:
                    # Tag Display Box
                    st.markdown(f"""
                        <div style="background-color:#1E1E1E; color:#00FF00; padding:10px; border-radius:5px; border:1px solid #333; text-align:center; margin-bottom:10px;">
                            <b>{tag}</b>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Delete Button right below the tag
                    if st.button("🗑️ Delete", key=f"del_{tag}_{i}", use_container_width=True):
                        supabase.table("custom_tags").delete().eq("tag_name", tag).execute()
                        st.success(f"{tag} Removed!")
                        time.sleep(0.5)
                        st.rerun()
        else:
            st.error("⚠️ Database se koi tag nahi mila! Check table: 'custom_tags'")
