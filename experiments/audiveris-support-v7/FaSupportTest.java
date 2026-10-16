package org.audiveris.omr.sheet.note;
import org.audiveris.omr.glyph.Shape;
import org.audiveris.omr.glyph.ShapeSet;
import org.junit.Test;
import static org.junit.Assert.*;
public class FaSupportTest {
 @Test public void defaultOff() { assertFalse(NoteHeadsBuilder.vetoFaSupport(Shape.NOTEHEAD_FA_LEFT_FILLED,0,10,false)); }
 @Test public void exactMajorityBoundary() { for(Shape s:ShapeSet.HeadsFa) { assertTrue(NoteHeadsBuilder.vetoFaSupport(s,4,10,true)); assertFalse(NoteHeadsBuilder.vetoFaSupport(s,5,10,true)); assertFalse(NoteHeadsBuilder.vetoFaSupport(s,6,10,true)); assertTrue(NoteHeadsBuilder.vetoFaSupport(s,0,0,true)); } }
 @Test public void ordinaryUnaffected() { for(Shape s:Shape.values()) if(!ShapeSet.HeadsFa.contains(s)) assertFalse(NoteHeadsBuilder.vetoFaSupport(s,0,10,true)); }
}
