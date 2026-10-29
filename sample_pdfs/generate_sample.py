"""
Generate sample farming advisory PDFs for Krishi Khoj testing.
Uses reportlab to create realistic Indian agricultural advisory documents.
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT


# ===== Color Scheme =====
PRIMARY_GREEN = HexColor('#2E7D32')
DARK_GREEN = HexColor('#1B5E20')
LIGHT_BG = HexColor('#F1F8E9')
HEADER_BG = HexColor('#C8E6C9')


def get_styles():
    """Create custom paragraph styles for the advisory documents."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='DocTitle',
        parent=styles['Title'],
        fontSize=22,
        textColor=DARK_GREEN,
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
    ))

    styles.add(ParagraphStyle(
        name='SubTitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=PRIMARY_GREEN,
        spaceAfter=8,
        alignment=TA_CENTER,
        fontName='Helvetica',
    ))

    styles.add(ParagraphStyle(
        name='SectionHead',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=DARK_GREEN,
        spaceBefore=16,
        spaceAfter=8,
        fontName='Helvetica-Bold',
    ))

    styles.add(ParagraphStyle(
        name='SubSection',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=PRIMARY_GREEN,
        spaceBefore=10,
        spaceAfter=6,
        fontName='Helvetica-Bold',
    ))

    styles.add(ParagraphStyle(
        name='BodyText11',
        parent=styles['Normal'],
        fontSize=11,
        leading=15,
        spaceAfter=6,
        alignment=TA_JUSTIFY,
        fontName='Helvetica',
    ))

    styles.add(ParagraphStyle(
        name='BulletItem',
        parent=styles['Normal'],
        fontSize=11,
        leading=15,
        leftIndent=20,
        spaceAfter=4,
        fontName='Helvetica',
    ))

    return styles


def add_header_footer(canvas, doc, crop_name):
    """Add header and footer to every page."""
    canvas.saveState()

    # Header
    canvas.setFillColor(DARK_GREEN)
    canvas.rect(0, A4[1] - 35, A4[0], 35, fill=True, stroke=False)
    canvas.setFillColor(HexColor('#FFFFFF'))
    canvas.setFont('Helvetica-Bold', 10)
    canvas.drawString(30, A4[1] - 24, f"Agricultural Advisory - {crop_name}")
    canvas.drawRightString(A4[0] - 30, A4[1] - 24, "Krishi Khoj Reference Document")

    # Footer
    canvas.setFillColor(DARK_GREEN)
    canvas.rect(0, 0, A4[0], 30, fill=True, stroke=False)
    canvas.setFillColor(HexColor('#FFFFFF'))
    canvas.setFont('Helvetica', 8)
    canvas.drawString(30, 10, "Government of India - Ministry of Agriculture & Farmers Welfare")
    canvas.drawRightString(A4[0] - 30, 10, f"Page {doc.page}")

    canvas.restoreState()


def generate_wheat_guide(output_dir):
    """Generate a 4-page Wheat Cultivation Guide PDF."""
    filepath = os.path.join(output_dir, "Wheat_Cultivation_Guide_2024.pdf")
    styles = get_styles()

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        topMargin=50,
        bottomMargin=45,
        leftMargin=40,
        rightMargin=40,
    )

    story = []

    # ===== PAGE 1: Title + Introduction =====
    story.append(Spacer(1, 40))
    story.append(Paragraph("Wheat Cultivation Guide 2024", styles['DocTitle']))
    story.append(Paragraph("Comprehensive Advisory for Rabi Season", styles['SubTitle']))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Directorate of Wheat Research, Indian Council of Agricultural Research",
        styles['SubTitle']
    ))
    story.append(Spacer(1, 30))

    story.append(Paragraph("1. Introduction", styles['SectionHead']))
    story.append(Paragraph(
        "Wheat is the second most important cereal crop of India after rice, contributing "
        "substantially to the national food security. India is the second largest producer of "
        "wheat in the world. Wheat is primarily a rabi season crop sown during October-November "
        "and harvested during March-April. The Indo-Gangetic plains of North India comprising "
        "Punjab, Haryana, and Uttar Pradesh account for about 65% of the total wheat production "
        "in the country.",
        styles['BodyText11']
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("1.1 Recommended Varieties for North India", styles['SubSection']))
    story.append(Paragraph(
        "The following improved wheat varieties are recommended for cultivation in the "
        "North-Western Plains Zone covering Punjab, Haryana, and western Uttar Pradesh:",
        styles['BodyText11']
    ))
    story.append(Paragraph(
        "\u2022 <b>HD-2967</b>: High yielding variety suitable for irrigated timely sown conditions. "
        "Average yield potential 50-55 q/ha. Resistant to yellow rust and leaf rust.",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "\u2022 <b>PBW-343</b>: Widely adapted variety for irrigated conditions. Semi-dwarf with "
        "good tillering capacity. Average yield 45-48 q/ha.",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "\u2022 <b>DBW-17</b>: Recommended for late sown irrigated conditions. Heat tolerant variety "
        "with yield potential of 40-45 q/ha.",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "\u2022 <b>WH-1105</b>: Suitable for restricted irrigation conditions in Haryana and Punjab. "
        "Good grain quality with bold grains.",
        styles['BulletItem']
    ))

    story.append(PageBreak())

    # ===== PAGE 2: Soil & Sowing =====
    story.append(Paragraph("2. Soil and Land Preparation", styles['SectionHead']))
    story.append(Paragraph(
        "Wheat grows best in well-drained loamy to clay loam soils with good organic matter "
        "content. The ideal soil pH range for wheat cultivation is 6.0 to 7.5. Saline and "
        "alkaline soils with pH above 8.5 should be avoided or reclaimed before sowing.",
        styles['BodyText11']
    ))
    story.append(Paragraph(
        "Land preparation involves 2-3 ploughings with a cultivator followed by planking to "
        "achieve a fine tilth. Laser leveling of fields is recommended for uniform irrigation "
        "and better crop stand. Incorporate FYM or compost at 10-15 tonnes per hectare during "
        "the last ploughing for improved soil fertility and structure.",
        styles['BodyText11']
    ))
    story.append(Paragraph(
        "Conservation tillage practices like zero tillage can save 1500-2000 rupees per hectare "
        "in land preparation costs while maintaining or improving yield levels. Zero till wheat "
        "also helps in timely sowing after rice harvest in the rice-wheat cropping system.",
        styles['BodyText11']
    ))

    story.append(Paragraph("3. Seed and Sowing", styles['SectionHead']))
    story.append(Paragraph("3.1 Seed Rate and Treatment", styles['SubSection']))
    story.append(Paragraph(
        "The recommended seed rate for wheat is 100 kg per hectare for timely sown conditions "
        "using a seed drill. For late sown conditions, increase the seed rate to 125 kg/ha to "
        "compensate for reduced tillering. Use only certified seed with germination above 85%.",
        styles['BodyText11']
    ))
    story.append(Paragraph(
        "Seed treatment is essential for protection against seed-borne diseases. Treat seed with "
        "Carboxin or Thiram at the rate of 2.5 g per kg of seed. For loose smut management, treat "
        "with Carbendazim at 2.5 g per kg seed or Tebuconazole 2DS at 1.5 g per kg seed. "
        "Seed treatment with Imidacloprid 600FS at 1.5 ml per kg seed protects against termites.",
        styles['BodyText11']
    ))

    story.append(Paragraph("3.2 Sowing Time and Method", styles['SubSection']))
    story.append(Paragraph(
        "The optimum sowing time for wheat in North India is October 25 to November 25 for "
        "timely sown varieties. Late sown varieties can be planted up to December 25 with "
        "appropriate adjustments in seed rate and variety selection. Sowing should be done in "
        "rows spaced 20 to 22.5 cm apart using a seed drill at a depth of 4-5 cm for proper "
        "germination and uniform crop stand.",
        styles['BodyText11']
    ))

    story.append(PageBreak())

    # ===== PAGE 3: Fertilizer & Irrigation =====
    story.append(Paragraph("4. Fertilizer Management", styles['SectionHead']))
    story.append(Paragraph(
        "The recommended fertilizer dose for irrigated wheat is 120:60:40 kg N:P:K per hectare. "
        "Apply half of the nitrogen (60 kg N/ha) along with the full dose of phosphorus (60 kg "
        "P2O5/ha) and full potassium (40 kg K2O/ha) as basal dose at the time of sowing.",
        styles['BodyText11']
    ))
    story.append(Paragraph(
        "The remaining nitrogen should be applied in two equal splits: first top dressing of "
        "30 kg N/ha at the time of first irrigation (21 DAS, crown root initiation stage), and "
        "second top dressing of 30 kg N/ha at the time of second irrigation (tillering stage). "
        "Use urea as the nitrogen source for top dressing.",
        styles['BodyText11']
    ))
    story.append(Paragraph(
        "For zinc deficient soils, apply zinc sulphate at 25 kg per hectare at the time of "
        "sowing. Apply FYM or farm yard manure at 10 to 15 tonnes per hectare 3-4 weeks before "
        "sowing. Green manuring with dhaincha or sunhemp before wheat sowing can supplement "
        "20-30 kg N/ha and improve soil organic carbon.",
        styles['BodyText11']
    ))

    story.append(Paragraph("5. Irrigation Management", styles['SectionHead']))
    story.append(Paragraph(
        "Wheat requires 5 to 6 irrigations for optimum production. The critical stages for "
        "irrigation in wheat are as follows:",
        styles['BodyText11']
    ))
    story.append(Paragraph(
        "\u2022 <b>Crown Root Initiation (CRI)</b>: First irrigation at 21 days after sowing (DAS). "
        "This is the most critical irrigation and should not be delayed.",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "\u2022 <b>Tillering Stage</b>: Second irrigation at 40-45 DAS for promoting tiller development.",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "\u2022 <b>Jointing Stage</b>: Third irrigation at 60-65 DAS when nodes begin to form.",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "\u2022 <b>Flowering Stage</b>: Fourth irrigation at 80-85 DAS during anthesis.",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "\u2022 <b>Milk Stage</b>: Fifth irrigation at 100-105 DAS when grains are in milk stage.",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "\u2022 <b>Dough Stage</b>: Sixth irrigation at 115-120 DAS during grain filling.",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "If water availability is limited, prioritize irrigations at CRI, flowering, and milk stages. "
        "Sprinkler irrigation can save 20-30% water compared to flood irrigation with comparable yields.",
        styles['BodyText11']
    ))

    story.append(PageBreak())

    # ===== PAGE 4: Pest Management & Yield =====
    story.append(Paragraph("6. Pest and Disease Management", styles['SectionHead']))
    story.append(Paragraph("6.1 Major Diseases", styles['SubSection']))
    story.append(Paragraph(
        "\u2022 <b>Yellow Rust (Stripe Rust)</b>: Most destructive disease of wheat in North India. "
        "Appears as yellow-orange pustules in stripes on leaves. Spray Propiconazole 25EC at "
        "the rate of 1 ml per litre of water as soon as symptoms appear. Repeat after 15 days "
        "if disease persists.",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "\u2022 <b>Karnal Bunt</b>: Affects individual grains in the ear head, producing black "
        "powdery mass with fishy smell. Spray Propiconazole 25EC at boot stage for preventive "
        "control. Use disease-free certified seed.",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "\u2022 <b>Loose Smut</b>: Entire ear head is replaced by black powdery spore mass. "
        "Manage through seed treatment with Carbendazim or Carboxin at 2.5 g/kg seed.",
        styles['BulletItem']
    ))

    story.append(Paragraph("6.2 Major Insect Pests", styles['SubSection']))
    story.append(Paragraph(
        "\u2022 <b>Termites</b>: Damage roots and lower stem causing drying of plants in patches. "
        "Apply Chlorpyrifos 20EC at 4 ml per litre of water as soil drench near the affected "
        "plants. Seed treatment with Imidacloprid also provides early protection.",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "\u2022 <b>Aphids</b>: Suck sap from leaves and ear heads during grain filling stage. "
        "Spray Dimethoate 30EC at 1 ml per litre of water or Imidacloprid 17.8SL at 0.5 ml "
        "per litre when aphid population exceeds economic threshold level.",
        styles['BulletItem']
    ))

    story.append(Paragraph("7. Expected Yield", styles['SectionHead']))
    story.append(Paragraph(
        "Under recommended management practices and timely sown irrigated conditions, the "
        "expected yield of improved wheat varieties is 45 to 50 quintals per hectare. Late "
        "sown wheat yields 35-40 q/ha. Under rainfed conditions in North India, wheat yield "
        "ranges from 20-25 q/ha depending on rainfall distribution. Adoption of all "
        "recommended practices including balanced fertilization, timely irrigation, and "
        "integrated pest management can help achieve the maximum potential yield.",
        styles['BodyText11']
    ))

    # Build PDF
    doc.build(
        story,
        onFirstPage=lambda c, d: add_header_footer(c, d, "Wheat"),
        onLaterPages=lambda c, d: add_header_footer(c, d, "Wheat"),
    )
    print(f"Generated: {filepath}")
    return filepath


def generate_rice_guide(output_dir):
    """Generate a 4-page Rice Production Technology PDF."""
    filepath = os.path.join(output_dir, "Rice_Production_Technology_2024.pdf")
    styles = get_styles()

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        topMargin=50,
        bottomMargin=45,
        leftMargin=40,
        rightMargin=40,
    )

    story = []

    # ===== PAGE 1: Title + Introduction =====
    story.append(Spacer(1, 40))
    story.append(Paragraph("Rice Production Technology 2024", styles['DocTitle']))
    story.append(Paragraph("Package of Practices for Kharif Season", styles['SubTitle']))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Indian Institute of Rice Research, ICAR - Hyderabad",
        styles['SubTitle']
    ))
    story.append(Spacer(1, 30))

    story.append(Paragraph("1. Introduction", styles['SectionHead']))
    story.append(Paragraph(
        "Rice (Oryza sativa L.) is the staple food crop for more than 65% of the Indian "
        "population. India is the second largest producer of rice globally after China. Rice "
        "is primarily a kharif season crop grown during the monsoon period from June to "
        "November. The major rice growing states include West Bengal, Uttar Pradesh, Punjab, "
        "Tamil Nadu, Andhra Pradesh, Bihar, and Odisha.",
        styles['BodyText11']
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("1.1 Recommended Varieties", styles['SubSection']))
    story.append(Paragraph(
        "Selection of appropriate variety is the key to successful rice cultivation. The "
        "following high yielding varieties are recommended for different regions:",
        styles['BodyText11']
    ))
    story.append(Paragraph(
        "\u2022 <b>Pusa Basmati 1121</b>: Premium basmati variety for North India with excellent "
        "grain quality and aroma. Grain length 8.3 mm, yield potential 40-45 q/ha. Recommended "
        "for Punjab, Haryana, and western Uttar Pradesh.",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "\u2022 <b>Pusa-44</b>: High yielding non-basmati variety with yield potential of 55-65 "
        "q/ha under irrigated conditions. Long duration variety (155-160 days). Suitable for "
        "Punjab and Haryana.",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "\u2022 <b>PR-126</b>: Short duration variety (123 days) recommended for Punjab. Yield "
        "potential 35-38 q/ha. Ideal for rice-wheat rotation to allow timely wheat sowing.",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "\u2022 <b>Swarna (MTU-7029)</b>: Most widely cultivated variety in eastern India. Semi-tall "
        "with yield potential of 50-55 q/ha. Recommended for Bihar, West Bengal, Odisha, and "
        "Chhattisgarh.",
        styles['BulletItem']
    ))

    story.append(PageBreak())

    # ===== PAGE 2: Nursery & Transplanting =====
    story.append(Paragraph("2. Nursery Management and Transplanting", styles['SectionHead']))
    story.append(Paragraph("2.1 Nursery Raising", styles['SubSection']))
    story.append(Paragraph(
        "Nursery beds should be prepared in the month of May-June depending on the variety "
        "and region. The seed rate for transplanted rice is 20 to 25 kg per hectare. For the "
        "System of Rice Intensification (SRI), the seed rate is reduced to 5-7 kg per hectare. "
        "Nursery area should be one-twentieth of the main field area.",
        styles['BodyText11']
    ))
    story.append(Paragraph(
        "Treat the seed with Carbendazim 50WP at 2 g per kg seed for protection against seed-borne "
        "diseases. Soak seed in water for 24 hours and incubate for another 24 hours for uniform "
        "germination. Apply 1 kg each of N and P2O5 per 100 sq m nursery area.",
        styles['BodyText11']
    ))

    story.append(Paragraph("2.2 Transplanting", styles['SubSection']))
    story.append(Paragraph(
        "Transplanting should be done when seedlings are 20 to 25 days old (3-4 leaf stage). "
        "For SRI method, younger seedlings of 12-14 days with 2 leaves are used. The recommended "
        "spacing for transplanting is 20 x 15 cm (row to row x plant to plant) for high yielding "
        "varieties. For basmati varieties, use 20 x 20 cm spacing. Plant 2-3 seedlings per hill "
        "at a depth of 2-3 cm in the puddled field.",
        styles['BodyText11']
    ))

    story.append(Paragraph("2.3 Soil Requirements", styles['SubSection']))
    story.append(Paragraph(
        "Rice grows well in puddled clay to clay loam soils with good water holding capacity. "
        "The ideal soil pH for rice cultivation is 5.5 to 6.5. Rice is also tolerant of slightly "
        "acidic conditions unlike wheat. Puddling of the field with 2-3 passes of a puddler in "
        "standing water helps in weed control, reduces percolation losses, and creates an "
        "anaerobic environment favorable for rice growth.",
        styles['BodyText11']
    ))

    story.append(PageBreak())

    # ===== PAGE 3: Fertilizer & Irrigation =====
    story.append(Paragraph("3. Fertilizer Management", styles['SectionHead']))
    story.append(Paragraph(
        "The recommended fertilizer dose for irrigated transplanted rice is 100:50:50 kg N:P:K "
        "per hectare. Apply the full dose of phosphorus (50 kg P2O5/ha) and potassium (50 kg "
        "K2O/ha) as basal application at the time of last puddling before transplanting.",
        styles['BodyText11']
    ))
    story.append(Paragraph(
        "Nitrogen should be applied in three splits: one-third (33 kg N/ha) as basal at "
        "transplanting, one-third at active tillering stage (25-30 days after transplanting), "
        "and the remaining one-third at panicle initiation stage (55-60 days after transplanting). "
        "Use the Leaf Color Chart (LCC) for need-based nitrogen management to improve nitrogen "
        "use efficiency.",
        styles['BodyText11']
    ))
    story.append(Paragraph(
        "Green manuring with Dhaincha (Sesbania aculeata) sown 60 days before transplanting "
        "and incorporated at flowering can substitute 25-30 kg nitrogen per hectare. Apply zinc "
        "sulphate at 25 kg/ha for zinc-deficient soils, particularly in alkaline and calcareous soils.",
        styles['BodyText11']
    ))

    story.append(Paragraph("4. Irrigation Management", styles['SectionHead']))
    story.append(Paragraph(
        "Maintain 5 cm standing water in the field during the vegetative phase of the rice crop "
        "from transplanting to tillering. During the reproductive phase, maintain 2-3 cm water. "
        "The Alternate Wetting and Drying (AWD) technique can save 20-25% irrigation water "
        "without yield loss. In AWD, allow the field to dry until hairline cracks appear before "
        "re-irrigating.",
        styles['BodyText11']
    ))
    story.append(Paragraph(
        "Critical stages for irrigation in rice are: transplanting, active tillering, panicle "
        "initiation, flowering, and grain filling. Drain the field 10-15 days before harvest "
        "to facilitate uniform maturity and easy harvesting. Continuous flooding should be "
        "avoided as it leads to higher methane emissions and water wastage.",
        styles['BodyText11']
    ))

    story.append(PageBreak())

    # ===== PAGE 4: Pest Management & Yield =====
    story.append(Paragraph("5. Pest and Disease Management", styles['SectionHead']))
    story.append(Paragraph("5.1 Major Insect Pests", styles['SubSection']))
    story.append(Paragraph(
        "\u2022 <b>Stem Borer (Scirpophaga incertulas)</b>: Causes dead hearts in vegetative stage "
        "and white ears in reproductive stage. Apply Cartap hydrochloride 4G granules at the rate "
        "of 25 kg per hectare in standing water at 30 days after transplanting. Alternatively, "
        "spray Chlorantraniliprole 18.5SC at 0.3 ml per litre.",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "\u2022 <b>Brown Plant Hopper (BPH)</b>: Causes hopper burn at the base of tillers. Avoid "
        "excess nitrogen application which increases BPH incidence. Spray Imidacloprid 17.8SL at "
        "0.5 ml per litre of water directed at the base of plants. Drain excess water before spraying.",
        styles['BulletItem']
    ))

    story.append(Paragraph("5.2 Major Diseases", styles['SubSection']))
    story.append(Paragraph(
        "\u2022 <b>Blast (Magnaporthe oryzae)</b>: Causes diamond-shaped lesions on leaves and neck "
        "rot. Spray Tricyclazole 75WP at the rate of 0.6 g per litre of water at tillering and "
        "boot stage. Avoid excess nitrogen and maintain optimum plant spacing.",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "\u2022 <b>Sheath Blight (Rhizoctonia solani)</b>: Causes oval to irregular lesions on "
        "leaf sheaths near water level. Spray Hexaconazole 5EC at 1 ml per litre of water or "
        "Validamycin 3L at 2 ml per litre. Reduce nitrogen dose in endemic areas.",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "\u2022 <b>Bacterial Leaf Blight (Xanthomonas oryzae)</b>: Causes yellow to white lesions "
        "from leaf tips. No effective chemical control; use resistant varieties. Avoid excess "
        "nitrogen and drain excess water.",
        styles['BulletItem']
    ))

    story.append(Paragraph("6. Expected Yield", styles['SectionHead']))
    story.append(Paragraph(
        "Under recommended package of practices, the expected yield of high yielding rice "
        "varieties is 55 to 65 quintals per hectare for Pusa-44 under irrigated conditions "
        "in Punjab and Haryana. Basmati varieties yield 40-45 q/ha. Short duration varieties "
        "like PR-126 yield 35-38 q/ha. In eastern India, Swarna yields 50-55 q/ha under "
        "good management. Average national productivity of rice is about 26 q/ha, indicating "
        "significant scope for yield improvement through adoption of recommended technologies "
        "and integrated crop management practices.",
        styles['BodyText11']
    ))

    # Build PDF
    doc.build(
        story,
        onFirstPage=lambda c, d: add_header_footer(c, d, "Rice / Paddy"),
        onLaterPages=lambda c, d: add_header_footer(c, d, "Rice / Paddy"),
    )
    print(f"Generated: {filepath}")
    return filepath


def main():
    """Generate both sample PDFs."""
    output_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(output_dir, exist_ok=True)

    print("Generating sample farming advisory PDFs...")
    print("=" * 50)

    wheat_path = generate_wheat_guide(output_dir)
    rice_path = generate_rice_guide(output_dir)

    print("=" * 50)
    print("Sample PDFs generated successfully!")
    print(f"  1. {wheat_path}")
    print(f"  2. {rice_path}")
    print("\nYou can now upload these to Krishi Khoj for testing.")


if __name__ == '__main__':
    main()
