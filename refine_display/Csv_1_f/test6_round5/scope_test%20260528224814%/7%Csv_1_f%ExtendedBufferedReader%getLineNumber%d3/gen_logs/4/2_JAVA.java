package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import static org.junit.jupiter.api.Assertions.assertEquals;

import java.io.StringReader;
import java.lang.reflect.Field;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class ExtendedBufferedReader_7_4Test {
    private ExtendedBufferedReader extendedBufferedReader;

    @BeforeEach
    void setUp() {
        extendedBufferedReader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2\nLine 3"));
    }

    @Test
    void testgetLineNumber_initialValue() throws Exception {
        // Access the private field lineCounter using reflection
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        lineCounterField.set(extendedBufferedReader, 0);

        // Invoke the method
        int lineNumber = extendedBufferedReader.getLineNumber();

        // Assert the expected line number
        assertEquals(0, lineNumber);
    }

    @Test
    void testgetLineNumber_afterReadingLines() throws Exception {
        // Simulate reading lines to increment the lineCounter
        extendedBufferedReader.readLine(); // Read first line
        extendedBufferedReader.readLine(); // Read second line

        // Access the private field lineCounter using reflection
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        lineCounterField.set(extendedBufferedReader, 2); // Simulate lineCounter being 2

        // Invoke the method
        int lineNumber = extendedBufferedReader.getLineNumber();

        // Assert the expected line number
        assertEquals(2, lineNumber);
    }

    @Test
    void testgetLineNumber_afterMultipleReads() throws Exception {
        // Simulate reading lines
        extendedBufferedReader.readLine(); // Read first line
        extendedBufferedReader.readLine(); // Read second line
        extendedBufferedReader.readLine(); // Read third line

        // Access the private field lineCounter using reflection
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        lineCounterField.set(extendedBufferedReader, 3); // Simulate lineCounter being 3

        // Invoke the method
        int lineNumber = extendedBufferedReader.getLineNumber();

        // Assert the expected line number
        assertEquals(3, lineNumber);
    }
}