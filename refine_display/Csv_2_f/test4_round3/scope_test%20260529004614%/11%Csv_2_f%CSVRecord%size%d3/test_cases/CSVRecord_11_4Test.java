package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.util.Collections;
import java.util.HashMap;

public class CSVRecord_11_4Test {

    @Test
    public void testSize_emptyArray() throws Exception {
        String[] values = new String[0];
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 0);
        Assertions.assertEquals(0, record.size());
    }

    @Test
    public void testSize_nonEmptyArray() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 0);
        Assertions.assertEquals(3, record.size());
        Assertions.assertEquals("value1", record.get(0));
        Assertions.assertEquals("value2", record.get(1));
        Assertions.assertEquals("value3", record.get(2));
    }

    @Test
    public void testSize_singleElementArray() throws Exception {
        String[] values = {"singleValue"};
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 0);
        Assertions.assertEquals(1, record.size());
        Assertions.assertEquals("singleValue", record.get(0));
    }

    @Test
    public void testSize_nullValuesArray() throws Exception {
        String[] values = null;
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 0);
        Field valuesField = CSVRecord.class.getDeclaredField("values");
        valuesField.setAccessible(true);
        valuesField.set(record, new String[0]); // Simulating null values as empty array
        Assertions.assertEquals(0, record.size());
    }

    @Test
    public void testSize_largeArray() throws Exception {
        String[] values = new String[1000];
        Arrays.fill(values, "value");
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 0);
        Assertions.assertEquals(1000, record.size());
        Assertions.assertEquals("value", record.get(0));
        Assertions.assertEquals("value", record.get(999));
    }

    @Test
    public void testSize_boundaryValues() throws Exception {
        String[] values = new String[1];
        values[0] = "boundaryValue";
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 0);
        Assertions.assertEquals(1, record.size());
        Assertions.assertEquals("boundaryValue", record.get(0));
        
        CSVRecord emptyRecord = new CSVRecord(new String[0], Collections.emptyMap(), null, 0);
        Assertions.assertEquals(0, emptyRecord.size());
    }

    @Test
    public void testGetOutOfBounds() throws Exception {
        String[] values = {"value1", "value2"};
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 0);
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            record.get(2);
        });
    }
}