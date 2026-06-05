import io
from typing import List, Any
from fpdf import FPDF
import matplotlib
matplotlib.use('Agg') # Necessary for server environments
import matplotlib.pyplot as plt

def clean_text(text):
    if not text: return ""
    # More robust cleaning
    text = str(text)
    replacements = {
        '\u2013': '-', '\u2014': '-', '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"', '\u2022': '*', '\u2026': '...',
        '\u00a0': ' ', '\u200b': '', '\u2010': '-', '\u2011': '-'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Final safety pass: remove any remaining non-latin1 characters
    return text.encode('latin-1', 'ignore').decode('latin-1')

def generate_pdf(session_title: str, messages: List[Any]):
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # Header
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 15, clean_text(session_title or "Data Analysis Report"), ln=True, align="C")
        
        # Add generated ON timestamp in IST
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(100, 100, 100)
        import datetime
        ist_time = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
        pdf.cell(0, 5, f"Generated On: {ist_time.strftime('%Y-%m-%d %I:%M %p')} (IST)", ln=True, align="C")
        pdf.ln(5)
        
        for msg in messages:
            role = getattr(msg, 'role', 'assistant').upper()
            content = clean_text(getattr(msg, 'content', '') or "")
            viz_data = getattr(msg, 'data', None)
            
            # Message Metadata
            pdf.set_font("Helvetica", "B", 11)
            if role == "ASSISTANT":
                pdf.set_text_color(0, 80, 150)
            elif role == "SYSTEM":
                pdf.set_text_color(100, 100, 100)
            else:
                pdf.set_text_color(0, 0, 0)
            
            pdf.cell(0, 8, f"[{role}]", ln=True)
            
            # Message Content
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(40, 40, 40)
            pdf.multi_cell(0, 6, content)
            pdf.ln(2)

            # Visualizations!
            if viz_data and isinstance(viz_data, dict):
                try:
                    v_type = viz_data.get("type", "bar")
                    v_points = viz_data.get("data", [])
                    v_title = viz_data.get("title", "Insight Visualization")
                    v_x_label = viz_data.get("xAxis", "")
                    v_y_label = viz_data.get("yAxis", "")

                    if v_points and len(v_points) > 0:
                        # Clear any previous plots
                        plt.clf()
                        plt.figure(figsize=(7, 4))
                        
                        keys = list(v_points[0].keys())
                        x_key = v_x_label if (v_x_label and v_x_label in keys) else keys[0]
                        y_key = v_y_label if (v_y_label and v_y_label in keys) else (keys[1] if len(keys) > 1 else keys[0])
                        
                        x_vals = []
                        y_vals = []
                        for p in v_points:
                            x_val = p.get(x_key, p.get("x", p.get("name", "")))
                            y_val = p.get(y_key, p.get("y", p.get("value", 0)))
                            x_vals.append(str(x_val)[:15]) # truncate very long x labels
                            try:
                                y_vals.append(float(y_val))
                            except:
                                y_vals.append(0.0)

                        if v_type == "line":
                            plt.plot(x_vals, y_vals, marker='o', color='#005096', linewidth=2)
                        elif v_type == "scatter":
                            plt.scatter(x_vals, y_vals, color='#005096')
                        else:  # default to bar
                            plt.bar(x_vals, y_vals, color='#005096')

                        plt.title(v_title)
                        plt.xlabel(v_x_label or x_key)
                        plt.ylabel(v_y_label or y_key)
                        plt.xticks(rotation=45, ha='right')
                        plt.tight_layout()

                        # Save plot to buffer
                        import tempfile
                        import os
                        
                        # Use a temporary file since older FPDF versions struggle with BytesIO
                        tmp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                        tmp_img.close()
                        plt.savefig(tmp_img.name, format='png', dpi=150, bbox_inches='tight')
                        
                        # Add to PDF
                        pdf.image(tmp_img.name, w=min(pdf.epw, 160))
                        pdf.ln(5)
                        
                        # Cleanup
                        plt.close()
                        os.unlink(tmp_img.name)
                except Exception as viz_err:
                    import traceback
                    traceback.print_exc()
                    print(f"Error drawing viz in PDF: {viz_err}")
                    pdf.set_font("Helvetica", "I", 8)
                    pdf.cell(0, 5, f"[Chart could not be rendered: {viz_err}]", ln=True)

            pdf.ln(5)
            
        output = pdf.output()
        return io.BytesIO(output)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"PDF Error: {e}")
        return io.BytesIO(b"Error generating PDF content")
