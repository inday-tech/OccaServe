import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_dfd():
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # Styles
    process_style = dict(boxstyle='round,pad=0.5', facecolor='#e1f5fe', edgecolor='#01579b', linewidth=1.5)
    entity_style = dict(boxstyle='square,pad=0.5', facecolor='#fff3e0', edgecolor='#e65100', linewidth=1.5)
    store_style = dict(boxstyle='round,pad=0.3', facecolor='#f1f8e9', edgecolor='#33691e', linewidth=1.5)

    # 1. External Entities
    ax.text(1, 9, "Customer", bbox=entity_style, ha='center', va='center', fontsize=12)
    ax.text(9, 9, "Caterer", bbox=entity_style, ha='center', va='center', fontsize=12)
    ax.text(5, 0.5, "Admin", bbox=entity_style, ha='center', va='center', fontsize=12)

    # 2. Processes
    procs = [
        (5, 8, "1.0 Manage User\nAccounts & KYC"),
        (2, 6, "2.0 Maintain\nMarketplace"),
        (5, 6, "3.0 Process\nEvent Bookings"),
        (8, 6, "4.0 Verify Payments\n& OCR"),
        (5, 2, "5.0 Generate\nAnalytics Reports")
    ]
    for x, y, label in procs:
        ax.text(x, y, label, bbox=process_style, ha='center', va='center', fontsize=10, fontweight='bold')

    # 3. Data Stores
    stores = [
        (2, 4, "D1: Users File"),
        (5, 4, "D2: Services File"),
        (8, 4, "D3: Bookings File")
    ]
    for x, y, label in stores:
        # Open-ended box effect (simulated)
        ax.text(x, y, label, bbox=store_style, ha='center', va='center', fontsize=10)

    # 4. Arrows (Simplified)
    # Customer flows
    ax.annotate("", xy=(5, 8.5), xytext=(1.5, 9), arrowprops=dict(arrowstyle="->", color="black"))
    ax.text(3, 8.7, "Registration", fontsize=8)
    
    ax.annotate("", xy=(5, 6.5), xytext=(1, 8.5), arrowprops=dict(arrowstyle="->", color="black"))
    ax.text(2.5, 7, "Booking Request", fontsize=8)

    # Caterer flows
    ax.annotate("", xy=(2.5, 6.3), xytext=(8.5, 9), arrowprops=dict(arrowstyle="->", color="black"))
    ax.text(7, 7.5, "Menu Data", fontsize=8)

    # Process to Store
    ax.annotate("", xy=(2, 4.5), xytext=(2, 5.5), arrowprops=dict(arrowstyle="->", color="black"))
    ax.annotate("", xy=(5, 4.5), xytext=(5, 5.5), arrowprops=dict(arrowstyle="->", color="black"))
    ax.annotate("", xy=(8, 4.5), xytext=(8, 5.5), arrowprops=dict(arrowstyle="->", color="black"))

    # Store to Reports
    ax.annotate("", xy=(5, 2.5), xytext=(2, 3.5), arrowprops=dict(arrowstyle="->", color="gray", alpha=0.5))
    ax.annotate("", xy=(5, 2.5), xytext=(5, 3.5), arrowprops=dict(arrowstyle="->", color="gray", alpha=0.5))
    ax.annotate("", xy=(5, 2.5), xytext=(8, 3.5), arrowprops=dict(arrowstyle="->", color="gray", alpha=0.5))

    # Reports to Admin
    ax.annotate("", xy=(5, 1), xytext=(5, 1.5), arrowprops=dict(arrowstyle="->", color="black"))
    ax.text(5.2, 1.2, "Reports", fontsize=9)

    plt.title("OccaServe DFD Level 1 (System Decomposition)", fontsize=16, pad=20)
    plt.tight_layout()
    plt.savefig('documentation/dfd_level_1.png', dpi=300)
    print("Diagram saved to documentation/dfd_level_1.png")

if __name__ == "__main__":
    draw_dfd()
