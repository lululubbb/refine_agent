package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_7_4Test {
    private ExtendedBufferedReader reader;

    @BeforeEach
    void setUp() {
        reader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2\nLine 3"));
    }

    @Test
    void testgetLineNumber_initialValue() throws Exception {
        // Access the private field lineCounter using reflection
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        int initialLineCount = (int) lineCounterField.get(reader);
        
        Assertions.assertEquals(0, initialLineCount);
    }

    @Test
    void testgetLineNumber_afterReadingLines() throws Exception {
        // Simulate reading lines
        reader.readLine(); // Reads Line 1
        reader.readLine(); // Reads Line 2
        
        // Access the private field lineCounter using reflection
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        int lineCountAfterReading = (int) lineCounterField.get(reader);
        
        Assertions.assertEquals(2, lineCountAfterReading);
    }

    @Test
    void testgetLineNumber_afterReadingAllLines() throws Exception {
        // Read all lines
        reader.readLine(); // Reads Line 1
        reader.readLine(); // Reads Line 2
        reader.readLine(); // Reads Line 3
        
        // Access the private field lineCounter using reflection
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        int lineCountAfterAllReads = (int) lineCounterField.get(reader);
        
        Assertions.assertEquals(3, lineCountAfterAllReads);
    }
}