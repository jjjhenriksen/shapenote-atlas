package org.audiveris.omr.sheet.note;

import java.awt.Rectangle;
import org.junit.Test;
import static org.junit.Assert.*;
import org.audiveris.omr.glyph.Shape;
import org.audiveris.omr.glyph.ShapeSet;
import org.audiveris.omr.math.Rational;
import org.audiveris.omr.image.TemplateFactory;
import org.audiveris.omr.ui.symbol.MusicFamily;

public class StemlessHeadsTest {
    @Test public void wholeFamiliesHaveWholeDurationAndNoStem() {
        for (Shape shape : ShapeSet.AtlasStemless) {
            assertEquals(Rational.ONE, shape.getNoteDuration());
            assertTrue(shape.isStemLessHead());
            assertFalse(ShapeSet.StemHeads.contains(shape));
            assertTrue(ShapeSet.HollowHeads.contains(shape));
            assertNotNull(shape.getHeadMotif());
        }
    }
    @Test public void glyphTemplatesExistAndHaveClosedInterior() {
        org.audiveris.omr.ui.symbol.MusicFont.populateAllSymbols();
        var catalog = TemplateFactory.getInstance().getCatalog(MusicFamily.Bravura, 48);
        for (Shape shape : ShapeSet.AtlasStemless) {
            var template = catalog.getTemplate(shape);
            assertNotNull(template);
            assertTrue(template.getKeyPoints().stream().anyMatch(p -> p.d < 0));
        }
    }
    @Test public void stemmedHalfAndQuarterAreNotWholes() {
        Rectangle head = new Rectangle(100,100,12,10);
        assertTrue(StemlessGuard.stemConflict(head,new Rectangle(111,75,1,35),3,10));
        assertTrue(StemlessGuard.stemConflict(head,new Rectangle(99,100,1,35),3,10));
    }
    @Test public void detachedNeighborStemAndShortHeadEdgesDoNotVeto() {
        Rectangle head = new Rectangle(100,100,12,10);
        assertFalse(StemlessGuard.stemConflict(head,new Rectangle(130,75,1,35),3,10));
        assertFalse(StemlessGuard.stemConflict(head,new Rectangle(111,100,1,10),3,10));
        assertFalse(StemlessGuard.stemConflict(head,new Rectangle(111,50,1,35),3,10));
    }
}
