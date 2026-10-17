package org.audiveris.omr.sheet.rhythm;

import org.junit.Test;
import ij.process.ByteProcessor;
import org.audiveris.omr.sheet.Staff;
import org.audiveris.omr.sheet.StaffLine;
import org.audiveris.omr.sheet.grid.LineInfo;
import java.awt.geom.Point2D;
import java.util.ArrayList;
import java.util.List;
import static org.junit.Assert.*;

public class BarConsensusTest {
    private Staff staff(int index) {
        List<LineInfo> lines=new ArrayList<>();
        for(int i=0;i<5;i++) lines.add(new StaffLine(List.of(new Point2D.Double(0,10+index*60+i*10),new Point2D.Double(240,10+index*60+i*10)),1));
        return new Staff(index+1,0,240,10,lines);
    }
    private BarConsensus.Mark mark(int staff, double x, int width, double coverage) {
        return new BarConsensus.Mark(staff, x, 10 + staff * 60, 50 + staff * 60, width, coverage);
    }
    @Test public void defaultOffDoesNotEvenAccessSystem() {
        String old = System.getProperty("atlas.barConsensus");
        System.clearProperty("atlas.barConsensus");
        try { assertEquals(0, BarConsensus.restore(null)); }
        finally { if (old != null) System.setProperty("atlas.barConsensus", old); }
    }
    @Test public void halfCoverageCannotRescueAColumn() {
        assertTrue(BarConsensus.consensus(List.of(mark(0,100,2,1),mark(3,100,2,1)),4,12).isEmpty());
    }
    @Test public void strictPixelMajorityRescuesWithoutLabelOrCountInput() {
        assertEquals(1,BarConsensus.consensus(List.of(mark(0,100,2,1),mark(1,101,2,1),mark(3,100,2,1)),4,12).size());
    }
    @Test public void duplicateStaffVotesCannotManufactureConsensus() {
        assertTrue(BarConsensus.consensus(List.of(mark(0,100,2,1),mark(0,101,2,1),mark(1,100,2,1)),4,12).isEmpty());
    }
    @Test public void brokenVerticalsAndWideMarksAreRejected() {
        for(double coverage:List.of(.85,Double.NaN))
            assertTrue(BarConsensus.consensus(List.of(mark(0,100,2,coverage),mark(1,100,2,coverage),mark(2,100,2,coverage)),4,12).isEmpty());
        assertTrue(BarConsensus.consensus(List.of(mark(0,100,8,1),mark(1,100,8,1),mark(2,100,8,1)),4,12).isEmpty());
    }
    @Test public void exactCoverageBoundaryAndCompleteLinkClustering() {
        assertEquals(1,BarConsensus.consensus(List.of(mark(0,100,2,.86),mark(1,100,2,.86),mark(2,100,2,.86)),4,12).size());
        assertTrue(BarConsensus.consensus(List.of(mark(0,100,2,1),mark(1,104,2,1),mark(2,108,2,1)),4,12).isEmpty());
    }
    @Test public void malformedInputsAbstainAndInputsAreNotMutated() {
        List<BarConsensus.Mark> input=new ArrayList<>(List.of(mark(2,100,2,1),mark(0,100,2,1),mark(1,100,2,1)));
        List<BarConsensus.Mark> saved=new ArrayList<>(input);
        BarConsensus.consensus(input,4,12);assertEquals(saved,input);
        assertTrue(BarConsensus.consensus(input,1,12).isEmpty());
        assertTrue(BarConsensus.consensus(input,4,Double.NaN).isEmpty());
    }
    @Test public void scannerRequiresFullVerticalInkAndPreservesOriginalPixels() {
        ByteProcessor pixels=new ByteProcessor(240,260);pixels.setColor(255);pixels.fill();
        for(int x=60;x<=61;x++) for(int y=10;y<=50;y++) pixels.set(x,y,0);
        for(int y=20;y<=40;y++) pixels.set(120,y,0);
        byte[] original=((byte[])pixels.getPixels()).clone();
        List<BarConsensus.Mark> marks=BarConsensus.scan(pixels,0,staff(0),10,230);
        assertEquals(1,marks.size());assertEquals(60.5,marks.getFirst().x(),0);
        assertArrayEquals(original,(byte[])pixels.getPixels());
    }
    @Test public void imageConsensusRejectsAlignedPartialStemsAndKeepsMissingStaffInDenominator() {
        ByteProcessor pixels=new ByteProcessor(240,260);pixels.setColor(255);pixels.fill();
        List<BarConsensus.Mark> marks=new ArrayList<>();
        for(int i=0;i<4;i++) {
            for(int y=10+i*60;y<=50+i*60;y++) {
                if(i!=2) pixels.set(60,y,0);
                if(i<2) pixels.set(160,y,0);
            }
            for(int y=20+i*60;y<=40+i*60;y++) pixels.set(120,y,0);
            marks.addAll(BarConsensus.scan(pixels,i,staff(i),10,230));
        }
        List<List<BarConsensus.Mark>> columns=BarConsensus.consensus(marks,4,10);
        assertEquals(1,columns.size());assertEquals(3,columns.getFirst().size());
        assertEquals(60,columns.getFirst().getFirst().x(),0);
    }
}
