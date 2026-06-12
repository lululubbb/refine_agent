package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Constructor;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_11_4Test {

    @Test
    public void testSize_emptyArray() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{});
        Assertions.assertEquals(0, record.size(), "Expected size to be 0 for an empty array");
    }

    @Test
    public void testSize_singleElementArray() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{"value1"});
        Assertions.assertEquals(1, record.size(), "Expected size to be 1 for a single element array");
        Assertions.assertEquals("value1", record.get(0), "Expected first element to be 'value1'");
    }

    @Test
    public void testSize_multipleElementsArray() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{"value1", "value2", "value3"});
        Assertions.assertEquals(3, record.size(), "Expected size to be 3 for three elements");
        Assertions.assertEquals("value1", record.get(0), "Expected first element to be 'value1'");
        Assertions.assertEquals("value2", record.get(1), "Expected second element to be 'value2'");
        Assertions.assertEquals("value3", record.get(2), "Expected third element to be 'value3'");
    }

    @Test
    public void testSize_boundaryValue() throws Exception {
        String[] values = new String[1000]; // boundary value
        Arrays.fill(values, "value");
        CSVRecord record = createCSVRecord(values);
        Assertions.assertEquals(1000, record.size(), "Expected size to be 1000 for the boundary value");
        for (int i = 0; i < 1000; i++) {
            Assertions.assertEquals("value", record.get(i), "Expected value at index " + i + " to be 'value'");
        }
    }

    @Test
    public void testSize_largeArray() throws Exception {
        String[] values = new String[10000]; // testing large array
        Arrays.fill(values, "largeValue");
        CSVRecord record = createCSVRecord(values);
        Assertions.assertEquals(10000, record.size(), "Expected size to be 10000 for a large array");
        for (int i = 0; i < 10000; i++) {
            Assertions.assertEquals("largeValue", record.get(i), "Expected value at index " + i + " to be 'largeValue'");
        }
    }

    @Test
    public void testGetOutOfBounds() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{"value1", "value2"});
        Assertions.assertThrows(IndexOutOfBoundsException.class, () -> {
            record.get(2);
        }, "Expected IndexOutOfBoundsException when accessing index 2");
    }

    @Test
    public void testGetNegativeIndex() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{"value1", "value2"});
        Assertions.assertThrows(IndexOutOfBoundsException.class, () -> {
            record.get(-1);
        }, "Expected IndexOutOfBoundsException when accessing a negative index");
    }

    private CSVRecord createCSVRecord(String[] values) throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance(values, mapping, null, 0);
    }
}