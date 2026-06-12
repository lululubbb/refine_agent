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

        Assertions.assertEquals(0, lineNumber); // Assuming lineCounter is not incremented in readLine
    }

    @Test
    void testGetLineNumber_afterMultipleReads() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2\nLine 3"));

        reader.readLine(); // Read first line
        reader.readLine(); // Read second line
        int lineNumber = invokeGetLineNumber(reader);

        Assertions.assertEquals(0, lineNumber); // Assuming lineCounter is not incremented in readLine
    }

    private int invokeGetLineNumber(ExtendedBufferedReader reader) throws Exception {
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        return (int) lineCounterField.get(reader);
    }
}