import java.util.ArrayList;
import java.util.List;

/** Warehouse stock report, after the refactor: one job per method. */
public class Inventory {
    private static final int LOW_STOCK = 5;

    private final List<String> lines = new ArrayList<>();

    public void report(List<Item> items, double budget) {
        double total = 0;
        for (Item item : items) {
            total += item.price * item.qty;
            lines.add(row(item, total > budget));
        }
        lines.add(trailer(total, budget));
    }

    private String status(Item item) {
        if (item.qty == 0) {
            return "OUT";
        }
        if (item.qty < LOW_STOCK) {
            return "LOW";
        }
        return "OK";
    }

    private String row(Item item, boolean overBudget) {
        String tag = status(item);
        if (overBudget && !tag.equals("OUT")) {
            tag = "OVER";
        }
        return tag + " " + item.name + " x" + item.qty + " = " + (item.price * item.qty);
    }

    private String trailer(double total, double budget) {
        if (total > budget) {
            return "TOTAL " + total + " OVER BUDGET by " + (total - budget);
        }
        return "TOTAL " + total;
    }
}
