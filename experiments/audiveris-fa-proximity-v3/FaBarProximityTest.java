// SPDX-License-Identifier: AGPL-3.0-or-later
package org.audiveris.omr.sheet.note;
import org.audiveris.omr.glyph.Shape;
import org.audiveris.omr.glyph.ShapeSet;
import org.junit.Test;
import java.awt.Rectangle;
import java.awt.geom.Area;
import java.util.List;
import static org.junit.Assert.*;
public class FaBarProximityTest {
    private final Rectangle head = new Rectangle(10,10,12,10);
    private final List<Area> overlap = List.of(new Area(new Rectangle(15,0,2,50)));
    @Test public void defaultOffDoesNotVetoAnyFaOrientationOrFill() {
        for(var shape:ShapeSet.HeadsFa) assertFalse(NoteHeadsBuilder.vetoFaBar(shape,head,overlap,false));
    }
    @Test public void enabledVetoCoversAllLogicalFaShapes() {
        for(var shape:ShapeSet.HeadsFa) assertTrue(NoteHeadsBuilder.vetoFaBar(shape,head,overlap,true));
    }
    @Test public void ordinaryHeadsKeepNativeCompetition() {
        for(var shape:new Shape[]{Shape.NOTEHEAD_BLACK,Shape.NOTEHEAD_VOID,Shape.WHOLE_NOTE})
            assertFalse(NoteHeadsBuilder.vetoFaBar(shape,head,overlap,true));
    }
    @Test public void disjointAndBoundaryOnlyBoxesAreNotVetoed() {
        assertFalse(NoteHeadsBuilder.vetoFaBar(Shape.NOTEHEAD_FA_LEFT_FILLED,head,List.of(new Area(new Rectangle(22,0,2,50))),true));
    }
    @Test public void noDetectedBarsMeansNoAdditionalVeto() {
        assertFalse(NoteHeadsBuilder.vetoFaBar(Shape.NOTEHEAD_FA_LEFT_VOID,head,List.of(),true));
    }
}
