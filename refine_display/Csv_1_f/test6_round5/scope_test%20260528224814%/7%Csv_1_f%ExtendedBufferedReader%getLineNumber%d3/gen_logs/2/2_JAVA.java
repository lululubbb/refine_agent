package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_7_2Test {

    @Test
    void testGetLineNumber_initialValue() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("line1\nline2"));
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(0, lineNumber);
    }

    @Test
    void testGetLineNumber_afterReading() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("line1\nline2"));
        reader.readLine(); // Simulate reading a line
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(1, lineNumber);
    }

    @Test
    void testGetLineNumber_multipleReads() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("line1\nline2\nline3"));
        reader.readLine(); // Read first line
        reader.readLine(); // Read second line
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(2, lineNumber);
    }

    @Test
    void testGetLineNumber_noReads() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("line1\nline2"));
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(0, lineNumber);
    }

    private int invokeGetLineNumber(ExtendedBufferedReader reader) throws Exception {
        Field field = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        field.setAccessible(true);
        return (int) field.get(reader);
    }
}