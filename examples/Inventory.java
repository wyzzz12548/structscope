import java.util.ArrayList;
import java.util.List;

/** Warehouse stock report, first draft: everything in one loop. */
public class Inventory {
    private final List<String> lines = new ArrayList<>();

    public void report(List<Item> items, double budget) {
        double total = 0;
        for (Item item : items) {
            total += item.price * item.qty;
            String tag;
            if (item.qty == 0) {
                tag = "OUT";
            } else if (item.qty < 5) {
                tag = "LOW";
            } else {
                tag = "OK";
            }
            if (total > budget && !tag.equals("OUT")) {
                tag = "OVER";
            }
            lines.add(tag + " " + item.name + " x" + item.qty + " = " + (item.price * item.qty));
        }
        if (total > budget) {
            lines.add("TOTAL " + total + " OVER BUDGET by " + (total - budget));
        } else {
            lines.add("TOTAL " + total);
        }
    }
}
