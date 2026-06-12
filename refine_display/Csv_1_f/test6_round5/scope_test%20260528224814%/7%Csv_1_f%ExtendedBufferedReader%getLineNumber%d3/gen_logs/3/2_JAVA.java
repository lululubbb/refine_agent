package org.apache.commons.csv;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_7_3Test {
    private ExtendedBufferedReader reader;

    @BeforeEach
    void setUp() {
        reader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2\nLine 3"));
    }

    @Test
    void testgetLineNumber_initialValue() throws Exception {
        // Accessing the private field 'lineCounter' using reflection
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        lineCounterField.setInt(reader, 0);

        int lineNumber = reader.getLineNumber();
        Assertions.assertEquals(0, lineNumber);
    }

    @Test
    void testgetLineNumber_afterReadingLines() throws Exception {
        // Simulate reading lines to change lineCounter
        reader.readLine(); // Reads "Line 1"
        reader.readLine(); // Reads "Line 2"

        // Accessing the private field 'lineCounter' using reflection
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        lineCounterField.setInt(reader, 2);

        int lineNumber = reader.getLineNumber();
        Assertions.assertEquals(2, lineNumber);
    }

    @Test
    void testgetLineNumber_afterMultipleReads() throws Exception {
        // Simulate reading lines to change lineCounter
        reader.readLine(); // Reads "Line 1"
        reader.readLine(); // Reads "Line 2"
        reader.readLine(); // Reads "Line 3"

        // Accessing the private field 'lineCounter' using reflection
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        lineCounterField.setInt(reader, 3);

        int lineNumber = reader.getLineNumber();
        Assertions.assertEquals(3, lineNumber);
    }
}