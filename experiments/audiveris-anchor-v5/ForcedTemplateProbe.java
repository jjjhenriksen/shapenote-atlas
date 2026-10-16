package org.audiveris.omr.sheet.note;

import java.awt.Point;
import java.awt.Rectangle;
import java.nio.file.Files;
import java.nio.file.Path;
import org.audiveris.omr.glyph.Shape;
import org.audiveris.omr.image.Anchored.Anchor;
import org.audiveris.omr.image.ChamferDistance;
import org.audiveris.omr.image.DistanceTable;
import org.audiveris.omr.image.PixelDistance;
import org.audiveris.omr.image.Template;
import org.audiveris.omr.image.TemplateFactory.Catalog;
import org.audiveris.omr.sheet.Sheet;
import org.audiveris.omr.sheet.Staff;

/** Read-only forced scores; not proposals, thresholds, or source labels. */
final class ForcedTemplateProbe {
    private static final Shape[][] PAIRS = {
        {Shape.NOTEHEAD_BLACK, Shape.NOTEHEAD_VOID},
        {Shape.NOTEHEAD_DIAMOND_FILLED, Shape.NOTEHEAD_DIAMOND_VOID},
        {Shape.NOTEHEAD_FA_LEFT_FILLED, Shape.NOTEHEAD_FA_LEFT_VOID},
        {Shape.NOTEHEAD_FA_UP_RIGHT_FILLED, Shape.NOTEHEAD_FA_UP_RIGHT_VOID}
    };
    static void run(Sheet sheet, Staff staff, Catalog catalog, DistanceTable distances) {
        String file = System.getProperty("atlas.forcedTemplatePoints");
        if (file == null) return;
        String input = sheet.getStub().getBook().getInputPath().getFileName().toString();
        try {
            for (String row : Files.readAllLines(Path.of(file))) {
                String[] p = row.split("\t");
                if (!p[0].equals(input) || Integer.parseInt(p[2]) != staff.getId()) continue;
                double cx = Double.parseDouble(p[3]), cy = Double.parseDouble(p[4]);
                for (Shape[] pair : PAIRS) {
                    Template filled = catalog.getTemplate(pair[0]);
                    for (Anchor a : new Anchor[]{Anchor.MIDDLE_LEFT, Anchor.LEFT_STEM, Anchor.RIGHT_STEM}) {
                        for (int dx=-1; dx<=1; dx++) for (int dy=-1; dy<=1; dy++) {
                            Point common = pivot(filled, a, cx+dx, cy+dy);
                            for (String mode : new String[]{"center", "anchor"}) for (Shape shape : pair) {
                                Template t = catalog.getTemplate(shape);
                                Point q = mode.equals("anchor") ? common : pivot(t, a, cx+dx, cy+dy);
                                Rectangle box = t.getSlimBoundsAt(q.x, q.y, a);
                                Rectangle outer = t.getBoundsAt(q.x, q.y, a);
                                int[] count = new int[8]; // fore/all, fore/missing, back/all, back/ink, hole/all, hole/ink, unknown, out
                                for (PixelDistance k : t.getKeyPoints()) {
                                    int x=outer.x+k.x, y=outer.y+k.y;
                                    if (x<0 || y<0 || x>=distances.getWidth() || y>=distances.getHeight()) {count[7]++; continue;}
                                    int actual=distances.getValue(x,y);
                                    if (actual==ChamferDistance.VALUE_UNKNOWN) {count[6]++; continue;}
                                    int i=k.d==0 ? 0 : k.d>0 ? 2 : 4;
                                    count[i]++;
                                    if (i==0 ? actual!=0 : actual==0) count[i+1]++;
                                }
                                System.out.println("ANCHOR5|"+p[1]+"|"+staff.getId()+"|"+staff.getHeadPointSize()+"|"+mode+"|"+a+"|"+dx+"|"+dy+"|"+shape
                                    +"|"+q.x+"|"+q.y+"|"+outer.x+"|"+outer.y+"|"+box.getCenterX()+"|"+box.getCenterY()+"|"+box.width+"|"+box.height
                                    +"|"+t.evaluate(q.x,q.y,a,distances)+"|"+t.evaluateHole(q.x,q.y,a,distances)+"|"+java.util.Arrays.toString(count));
                            }
                        }
                    }
                }
            }
        } catch (java.io.IOException e) { throw new IllegalStateException(e); }
    }
    private static Point pivot(Template t, Anchor a, double cx, double cy) {
        Rectangle slim=t.getSlimBounds(); Point offset=t.getOffset(a);
        return new Point((int)Math.round(cx-slim.getCenterX())+offset.x,
                         (int)Math.round(cy-slim.getCenterY())+offset.y);
    }
}
