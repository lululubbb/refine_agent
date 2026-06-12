package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_7_6Test {

    @Test
    void testGetLineNumber_initialState() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));

        int lineNumber = invokeGetLineNumber(reader);

        Assertions.assertEquals(0, lineNumber);
    }

    @Test
    void testGetLineNumber_afterReadingLine() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("First line\nSecond line"));

        reader.readLine(); // Simulate reading a line
        int lineNumber = invokeGetLineNumber(reader);

        Assertions.assertEquals(1, lineNumber); // Expect 1 after reading the first line
    }

    @Test
    void testGetLineNumber_afterMultipleReads() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2\nLine 3"));

        reader.readLine(); // Read first line
        reader.readLine(); // Read second line
        int lineNumber = invokeGetLineNumber(reader);

        Assertions.assertEquals(2, lineNumber); // Expect 2 after reading two lines
    }

    @Test
    void testGetLineNumber_afterReadingAllLines() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2\nLine 3"));

        reader.readLine(); // Read first line
        reader.readLine(); // Read second line
        reader.readLine(); // Read third line
        int lineNumber = invokeGetLineNumber(reader);

        Assertions.assertEquals(3, lineNumber); // Expect 3 after reading all three lines
    }

    @Test
    void testGetLineNumber_afterReadingEmptyReader() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));

        int lineNumber = invokeGetLineNumber(reader);

        Assertions.assertEquals(0, lineNumber); // Expect 0 for an empty reader
    }

    private int invokeGetLineNumber(ExtendedBufferedReader reader) throws Exception {
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        return (int) lineCounterField.get(reader);
    }
}