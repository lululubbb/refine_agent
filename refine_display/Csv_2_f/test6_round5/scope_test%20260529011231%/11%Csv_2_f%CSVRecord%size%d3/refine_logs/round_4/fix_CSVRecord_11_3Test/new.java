package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_11_3Test {

    @Test
    public void testSize_emptyArray() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{});
        Assertions.assertEquals(0, record.size());
    }

    @Test
    public void testSize_singleElementArray() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{"value1"});
        Assertions.assertEquals(1, record.size());
        Assertions.assertEquals("value1", record.get(0));
    }

    @Test
    public void testSize_multipleElementsArray() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{"value1", "value2", "value3"});
        Assertions.assertEquals(3, record.size());
        Assertions.assertEquals("value1", record.get(0));
        Assertions.assertEquals("value2", record.get(1));
        Assertions.assertEquals("value3", record.get(2));
    }

    @Test
    public void testSize_largeArray() throws Exception {
        String[] values = new String[1000];
        Arrays.fill(values, "value");
        CSVRecord record = createCSVRecord(values);
        Assertions.assertEquals(1000, record.size());
        for (int i = 0; i < 1000; i++) {
            Assertions.assertEquals("value", record.get(i));
        }
    }

    @Test
    public void testSize_boundaryArray() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{"value1", "", "value3"});
        Assertions.assertEquals(3, record.size());
        Assertions.assertEquals("value1", record.get(0));
        Assertions.assertEquals("", record.get(1));
        Assertions.assertEquals("value3", record.get(2));
    }

    @Test
    public void testSize_largeEmptyArray() throws Exception {
        CSVRecord record = createCSVRecord(new String[1000]);
        Assertions.assertEquals(1000, record.size());
        for (int i = 0; i < 1000; i++) {
            Assertions.assertEquals(null, record.get(i)); // Expecting null for uninitialized strings
        }
    }

    @Test
    public void testGetOutOfBounds() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{"value1"});
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            record.get(1);
        });
    }

    @Test
    public void testGetNegativeIndex() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{"value1", "value2"});
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            record.get(-1);
        });
    }

    private CSVRecord createCSVRecord(String[] values) throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance(values, mapping, null, 0);
    }
}