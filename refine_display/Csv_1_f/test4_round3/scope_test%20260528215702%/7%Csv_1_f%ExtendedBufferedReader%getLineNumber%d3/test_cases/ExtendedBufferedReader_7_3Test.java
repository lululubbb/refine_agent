package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_7_3Test {

    @Test
    void testGetLineNumber_initialState() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));

        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(0, lineNumber);
    }

    @Test
    void testGetLineNumber_afterReading() throws Exception {
        String testInput = "First line\nSecond line\nThird line";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(testInput));

        // Simulate reading lines
        reader.readLine();
        reader.readLine();

        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(2, lineNumber);
    }

    @Test
    void testGetLineNumber_afterMultipleReads() throws Exception {
        String testInput = "Line 1\nLine 2\nLine 3\nLine 4";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(testInput));

        // Simulate reading multiple lines
        reader.readLine();
        reader.readLine();
        reader.readLine();

        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(3, lineNumber);
    }

    @Test
    void testGetLineNumber_afterReadingEmptyLine() throws Exception {
        String testInput = "First line\n\nSecond line";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(testInput));

        // Simulate reading lines including an empty one
        reader.readLine();
        reader.readLine(); // Read the empty line
        reader.readLine();

        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(3, lineNumber);
    }

    @Test
    void testGetLineNumber_afterReadingAllLines() throws Exception {
        String testInput = "Line 1\nLine 2\nLine 3";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(testInput));

        // Simulate reading all lines
        reader.readLine();
        reader.readLine();
        reader.readLine();

        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(3, lineNumber);
    }

    @Test
    void testGetLineNumber_withMixedLineEndings() throws Exception {
        String testInput = "Line 1\rLine 2\nLine 3\r\nLine 4";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(testInput));

        // Simulate reading lines with mixed line endings
        reader.readLine();
        reader.readLine();
        reader.readLine();

        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(3, lineNumber);
    }

    @Test
    void testGetLineNumber_afterReadingFromEmptyStream() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));

        // Simulate reading from an empty stream
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(0, lineNumber);
    }

    private int invokeGetLineNumber(ExtendedBufferedReader reader) throws Exception {
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        return (int) lineCounterField.get(reader);
    }
}