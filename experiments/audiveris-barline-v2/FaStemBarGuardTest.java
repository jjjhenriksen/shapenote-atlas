// SPDX-License-Identifier: AGPL-3.0-or-later
package org.audiveris.omr.sig;
import org.audiveris.omr.glyph.Shape;
import org.audiveris.omr.glyph.ShapeSet;
import org.audiveris.omr.sig.inter.*;
import org.junit.Test;
import java.awt.Rectangle;
import java.awt.geom.Line2D;
import java.util.Set;
import static org.junit.Assert.*;
public class FaStemBarGuardTest {
    private BarlineInter bar(double grade) { return new BarlineInter(null, Shape.THIN_BARLINE, grade, new Line2D.Double(10,0,10,50), 2.0); }
    private HeadInter head(Shape shape) { return new HeadInter(new Rectangle(8,20,12,10), shape, .9, null, 0.0); }
    private StemInter stem(HeadInter... heads) { return new StemInter(null,.9) { @Override public Set<HeadInter> getHeads() { return Set.of(heads); } }; }
    @Test public void defaultOffUsesUpstreamOrdering() {
        var b=bar(.2);var s=stem(head(Shape.NOTEHEAD_FA_LEFT_FILLED));
        assertSame(b,SIGraph.selectWeaker(b,s,false));assertSame(b,SIGraph.selectWeaker(s,b,false));
    }
    @Test public void faOnlyStemLosesDirectBarConflictInEitherOrder() {
        for(var shape:ShapeSet.HeadsFa) {var b=bar(.2);var s=stem(head(shape));
            assertSame(s,SIGraph.selectWeaker(b,s,true));assertSame(s,SIGraph.selectWeaker(s,b,true));}
    }
    @Test public void mixedHeadAndStandardStemsStillUseGrades() {
        var b=bar(.2);var s=stem(head(Shape.NOTEHEAD_FA_LEFT_FILLED),head(Shape.NOTEHEAD_BLACK));
        assertSame(b,SIGraph.selectWeaker(b,s,true));
        assertSame(b,SIGraph.selectWeaker(b,stem(head(Shape.NOTEHEAD_BLACK)),true));
    }
    @Test public void unsupportedStemDoesNotGetSpecialTreatment() {
        var b=bar(.2);assertSame(b,SIGraph.selectWeaker(b,stem(),true));
    }
    @Test public void directFaHeadConflictIsUnchanged() {
        var b=bar(.2);assertSame(b,SIGraph.selectWeaker(b,head(Shape.NOTEHEAD_FA_LEFT_FILLED),true));
    }
    @Test public void otherConflictsAndGradeTiesAreUnchanged() {
        var a=head(Shape.NOTEHEAD_FA_LEFT_FILLED);var b=head(Shape.NOTEHEAD_BLACK);
        assertSame(b,SIGraph.selectWeaker(a,b,true));
        var s=stem(a);assertSame(s,SIGraph.selectWeaker(b,s,true));
    }
}
