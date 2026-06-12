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
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        int initialLineCount = (int) lineCounterField.get(reader);
        
        Assertions.assertEquals(0, initialLineCount);
    }

    @Test
    void testgetLineNumber_afterReadingLines() throws Exception {
        reader.readLine(); // Reads Line 1
        reader.readLine(); // Reads Line 2
        
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        int lineCountAfterReading = (int) lineCounterField.get(reader);
        
        Assertions.assertEquals(2, lineCountAfterReading);
    }

    @Test
    void testgetLineNumber_afterReadingAllLines() throws Exception {
        reader.readLine(); // Reads Line 1
        reader.readLine(); // Reads Line 2
        reader.readLine(); // Reads Line 3
        
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        int lineCountAfterAllReads = (int) lineCounterField.get(reader);
        
        Assertions.assertEquals(3, lineCountAfterAllReads);
    }

    @Test
    void testgetLineNumber_afterReadingNoLines() throws Exception {
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        int lineCountAfterNoReads = (int) lineCounterField.get(reader);
        
        Assertions.assertEquals(0, lineCountAfterNoReads);
    }

    @Test
    void testgetLineNumber_afterReadingEmptyStream() throws Exception {
        ExtendedBufferedReader emptyReader = new ExtendedBufferedReader(new StringReader(""));
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        int lineCountAfterEmptyRead = (int) lineCounterField.get(emptyReader);
        
        Assertions.assertEquals(0, lineCountAfterEmptyRead);
    }

    @Test
    void testgetLineNumber_afterReadingWithDifferentLineEndings() throws Exception {
        ExtendedBufferedReader mixedReader = new ExtendedBufferedReader(new StringReader("Line 1\r\nLine 2\nLine 3\r"));
        mixedReader.readLine(); // Reads Line 1
        mixedReader.readLine(); // Reads Line 2
        mixedReader.readLine(); // Reads Line 3
        
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        int lineCountAfterMixedReads = (int) lineCounterField.get(mixedReader);
        
        Assertions.assertEquals(3, lineCountAfterMixedReads);
    }
}