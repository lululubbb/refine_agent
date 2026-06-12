package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_7_2Test {

    @Test
    void testgetLineNumber_initialValue() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(0, lineNumber);
    }

    @Test
    void testgetLineNumber_afterReading() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2"));
        reader.readLine(); // Simulate reading a line
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(1, lineNumber); // Expect lineCounter to be 1 after reading a line
    }

    @Test
    void testgetLineNumber_afterMultipleReads() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2\nLine 3"));
        reader.readLine(); // Read first line
        reader.readLine(); // Read second line
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(2, lineNumber); // Expect lineCounter to be 2 after reading two lines
    }

    @Test
    void testgetLineNumber_afterReadingEmptyString() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(0, lineNumber); // Expect lineCounter to be 0 for empty string
        reader.readLine(); // Read from empty string
        lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(0, lineNumber); // Should still be 0 after reading empty
    }

    @Test
    void testgetLineNumber_afterReadingLinesWithEmptyLine() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Line 1\n\nLine 2"));
        reader.readLine(); // Read first line
        reader.readLine(); // Read empty line
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(1, lineNumber); // Expect lineCounter to be 1 after reading first line and empty line
        reader.readLine(); // Read second line
        lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(2, lineNumber); // Expect lineCounter to be 2 after reading second line
    }

    private int invokeGetLineNumber(ExtendedBufferedReader reader) throws Exception {
        Field field = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        field.setAccessible(true);
        return (int) field.get(reader);
    }
}