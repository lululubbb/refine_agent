package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_7_1Test {

    @Test
    void testgetLineNumber_initialValue() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(0, lineNumber);
    }

    @Test
    void testgetLineNumber_afterReadingLines() throws Exception {
        String input = "First line\nSecond line\nThird line";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        // Simulate reading lines (the method is not provided, so we assume it increments lineCounter)
        reader.readLine(); // First line
        reader.readLine(); // Second line
        
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(2, lineNumber);
    }

    @Test
    void testgetLineNumber_noLinesRead() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Some text"));
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(0, lineNumber);
    }

    private int invokeGetLineNumber(ExtendedBufferedReader reader) throws Exception {
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        return (int) lineCounterField.get(reader);
    }
}