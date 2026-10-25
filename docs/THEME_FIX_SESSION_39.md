# Session 39 — Dark Mode Fix

The earlier implementation used Streamlit `--st-*` CSS custom properties in global app CSS. Those variables are intended for scoped component theming and were not reliable for this global layout.

This version resolves `st.context.theme.type` (`light` or `dark`) and builds the application palette in Python before injecting CSS. The native Streamlit config still supplies the actual widget theme and the Settings light/dark switch.

The dependency floor is raised to Streamlit 1.51 because dual light/dark custom themes were introduced in that release, and the runtime theme context is available from 1.46 onward.
