// SPDX-License-Identifier: AGPL-3.0-or-later
package org.audiveris.omr.sig;
import org.audiveris.omr.glyph.Shape;
import org.audiveris.omr.glyph.ShapeSet;
import org.audiveris.omr.sig.inter.*;
import org.junit.Test;
import java.awt.Rectangle;
import java.awt.geom.Line2D;
import static org.junit.Assert.*;
public class FaBarGuardTest {
    private BarlineInter bar(double grade) { return new BarlineInter(null, Shape.THIN_BARLINE, grade, new Line2D.Double(10,0,10,50), 2.0); }
    private HeadInter head(Shape shape,double grade) { return new HeadInter(new Rectangle(8,20,12,10), shape, grade, null, 0.0); }
    @Test public void defaultOffUsesUpstreamGradeOrdering() {
        var b=bar(.2); var h=head(Shape.NOTEHEAD_FA_LEFT_FILLED,.9);
        assertSame(b,SIGraph.selectWeaker(b,h,false)); assertSame(b,SIGraph.selectWeaker(h,b,false));
    }
    @Test public void onlyFaHeadLosesDirectPhysicalBarConflictInEitherOrder() {
        for (var shape:ShapeSet.HeadsFa) { var b=bar(.2); var h=head(shape,.9);
            assertSame(h,SIGraph.selectWeaker(b,h,true)); assertSame(h,SIGraph.selectWeaker(h,b,true)); }
    }
    @Test public void standardHeadsStillCompeteByGrade() {
        var b=bar(.2); var h=head(Shape.NOTEHEAD_BLACK,.9);
        assertSame(b,SIGraph.selectWeaker(b,h,true)); assertSame(b,SIGraph.selectWeaker(h,b,true));
    }
    @Test public void headHeadCompetitionAndTiesAreUnchanged() {
        var a=head(Shape.NOTEHEAD_FA_LEFT_FILLED,.2); var b=head(Shape.NOTEHEAD_BLACK,.9);
        assertSame(a,SIGraph.selectWeaker(a,b,true));
        var c=head(Shape.NOTEHEAD_BLACK,.2); assertSame(c,SIGraph.selectWeaker(a,c,true));
    }
}
