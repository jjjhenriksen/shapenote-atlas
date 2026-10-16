package org.audiveris.omr.sheet.note;
import org.audiveris.omr.glyph.Shape;
import org.junit.Test;
import static org.junit.Assert.*;
public class NativeFaHoleTest {
 @Test public void defaultOff() { assertNull(NoteHeadsBuilder.holePartner(Shape.NOTEHEAD_FA_LEFT_FILLED,false)); assertNull(NoteHeadsBuilder.holePartner(Shape.NOTEHEAD_FA_UP_RIGHT_FILLED,false)); }
 @Test public void ordinaryUnchanged() { assertEquals(Shape.NOTEHEAD_VOID,NoteHeadsBuilder.holePartner(Shape.NOTEHEAD_BLACK,false)); assertEquals(Shape.NOTEHEAD_VOID,NoteHeadsBuilder.holePartner(Shape.NOTEHEAD_BLACK,true)); }
 @Test public void orientationPreserved() { assertEquals(Shape.NOTEHEAD_FA_LEFT_VOID,NoteHeadsBuilder.holePartner(Shape.NOTEHEAD_FA_LEFT_FILLED,true)); assertEquals(Shape.NOTEHEAD_FA_UP_RIGHT_VOID,NoteHeadsBuilder.holePartner(Shape.NOTEHEAD_FA_UP_RIGHT_FILLED,true)); }
 @Test public void noOtherShapesChanged() { for(Shape s:Shape.values()) if(s!=Shape.NOTEHEAD_BLACK && s!=Shape.NOTEHEAD_FA_LEFT_FILLED && s!=Shape.NOTEHEAD_FA_UP_RIGHT_FILLED) assertNull(NoteHeadsBuilder.holePartner(s,true)); }
}
