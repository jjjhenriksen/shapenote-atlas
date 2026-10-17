package org.audiveris.omr.sheet.rhythm;

import ij.process.ByteProcessor;
import org.audiveris.omr.glyph.Grades;
import org.audiveris.omr.glyph.Shape;
import org.audiveris.omr.sheet.Picture;
import org.audiveris.omr.sheet.Staff;
import org.audiveris.omr.sheet.SystemInfo;
import org.audiveris.omr.sig.inter.BarlineInter;
import org.audiveris.omr.util.HorizontalSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.awt.geom.Line2D;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Default-off internal thin-bar recovery from original binary cross-staff ink.
 * No source coordinates, expected counts, score labels or pitch/shape rules.
 * Never changes existing bars or image bytes; recovered graph bars have no glyph.
 */
public final class BarConsensus {
    private static final Logger logger = LoggerFactory.getLogger(BarConsensus.class);
    static final double COVERAGE = .86;
    static final double CLUSTER = .35;

    private BarConsensus() {}

    record Mark(int staff, double x, int top, int bottom, int width, double coverage) {}

    static List<List<Mark>> consensus(List<Mark> marks, int staffCount, double interline) {
        List<List<Mark>> clusters = new ArrayList<>();
        if (staffCount < 2 || !Double.isFinite(interline) || interline < 3) return clusters;
        List<Mark> ordered = marks.stream().filter(m -> m.staff >= 0 && m.staff < staffCount
                && Double.isFinite(m.x) && Double.isFinite(m.coverage)
                && m.coverage >= COVERAGE && m.coverage <= 1
                && m.top >= 0 && m.bottom > m.top
                && m.width >= 1 && m.width <= CLUSTER * interline)
                .sorted(Comparator.comparingDouble(Mark::x)).toList();
        List<List<Mark>> raw = new ArrayList<>();
        for (Mark mark : ordered) {
            if (raw.isEmpty() || mark.x - raw.getLast().getFirst().x > CLUSTER * interline)
                raw.add(new ArrayList<>());
            raw.getLast().add(mark);
        }
        int required = Math.max(2, staffCount / 2 + 1);
        for (List<Mark> cluster : raw) {
            Map<Integer, Mark> perStaff = new HashMap<>();
            for (Mark mark : cluster) {
                Mark old = perStaff.get(mark.staff);
                if (old == null || mark.coverage > old.coverage) perStaff.put(mark.staff, mark);
            }
            if (perStaff.size() >= required)
                clusters.add(perStaff.values().stream().sorted(Comparator.comparingInt(Mark::staff)).toList());
        }
        return clusters;
    }

    static List<Mark> scan(ByteProcessor pixels, int staffIndex, Staff staff, int left, int right) {
        List<Mark> result = new ArrayList<>();
        int start = -1;
        double best = 0;
        for (int x = left; x <= right; x++) {
            double coverage = 0;
            if (x < right) {
                int top = (int) Math.rint(staff.getFirstLine().yAt(x));
                int bottom = (int) Math.rint(staff.getLastLine().yAt(x));
                if (top >= 0 && bottom < pixels.getHeight() && top < bottom) {
                    int ink = 0;
                    for (int y = top; y <= bottom; y++) if (pixels.get(x, y) == 0) ink++;
                    coverage = (double) ink / (bottom - top + 1);
                }
            }
            if (coverage >= COVERAGE) {
                if (start < 0) start = x;
                best = Math.max(best, coverage);
            } else if (start >= 0) {
                double center = (start + x - 1) / 2.0;
                result.add(new Mark(staffIndex, center,
                        (int) Math.rint(staff.getFirstLine().yAt(center)),
                        (int) Math.rint(staff.getLastLine().yAt(center)), x - start, best));
                start = -1; best = 0;
            }
        }
        return result;
    }

    public static int restore(SystemInfo system) {
        if (!Boolean.getBoolean("atlas.barConsensus")) return 0;
        List<Staff> staves = system.getStaves();
        // Abstain on unsupported/mixed systems rather than shrink the denominator.
        if (staves.size() < 2 || staves.stream().anyMatch(s -> s.isTablature() || s.getLines().size() != 5)) return 0;
        double spacing = staves.stream().mapToInt(Staff::getSpecificInterline).average().orElse(0);
        if (spacing < 3) return 0;
        // Interior only: do not synthesize brackets, staff-end, double or repeat groups.
        int left = (int) Math.ceil(staves.stream().mapToInt(s -> s.getAbscissa(HorizontalSide.LEFT)).max().orElse(0) + spacing);
        int right = (int) Math.floor(staves.stream().mapToInt(s -> s.getAbscissa(HorizontalSide.RIGHT)).min().orElse(0) - spacing);
        ByteProcessor pixels = system.getSheet().getPicture().getSource(Picture.SourceKey.BINARY);
        if (pixels == null || left < 0 || right > pixels.getWidth() || left >= right) return 0;
        List<Mark> marks = new ArrayList<>();
        for (int i = 0; i < staves.size(); i++) marks.addAll(scan(pixels, i, staves.get(i), left, right));
        List<List<Mark>> columns = consensus(marks, staves.size(), spacing);
        int restored = 0;
        for (List<Mark> column : columns) {
            for (Mark mark : column) {
                Staff staff = staves.get(mark.staff);
                if (staff.getBarlines().stream().anyMatch(b -> Math.abs(b.getCenter().x - mark.x) <= .5 * spacing)) continue;
                BarlineInter bar = new BarlineInter(null, Shape.THIN_BARLINE,
                        Grades.intrinsicRatio, new Line2D.Double(mark.x, mark.top, mark.x, mark.bottom), (double) mark.width);
                bar.setStaff(staff);
                system.getSig().addVertex(bar);
                bar.freeze();
                restored++;
                logger.info("AtlasBarConsensus S{} staff={} x={} support={}/{} coverage={} synthetic={}",
                        system.getId(), staff.getId(), mark.x, column.size(), staves.size(), mark.coverage, bar.getId());
            }
        }
        logger.info("AtlasBarConsensus S{} columns={} restored={}", system.getId(), columns.size(), restored);
        return restored;
    }
}
